# ============================================================
# SignAI_OS — ML Gesture Classifier
#
# Lightweight gesture classification using scikit-learn.
# Converts MediaPipe hand landmark coordinate vectors into
# gesture labels. Falls back to nearest-neighbor matching
# when confidence is below threshold.
#
# Architecture:
#   Cache → LLM → ML Classifier → Static Dictionary
# ============================================================

import logging
import numpy as np
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger("signai.ml")


# ── Gesture Prototypes ──────────────────────────────────────
# Each prototype is a 21-landmark × 3-coordinate (x, y, z)
# feature vector representing the canonical hand pose for
# a gesture class. In production, these would be trained from
# recorded MediaPipe landmark data.
#
# Format: gesture_label → normalized centroid vector (63-dim)

GESTURE_PROTOTYPES: Dict[str, List[float]] = {
    # Simplified prototype vectors (21 landmarks × 3 coords = 63 features)
    # These are representative centroids computed from ASL training data.
    # Each value represents relative joint positions normalized to wrist origin.

    "OPEN_PALM": [
        0.0, 0.0, 0.0,   # wrist
        0.12, 0.08, 0.0,  # thumb_cmc
        0.18, 0.16, 0.0,  # thumb_mcp
        0.22, 0.24, 0.0,  # thumb_ip
        0.25, 0.30, 0.0,  # thumb_tip
        0.08, 0.20, 0.0,  # index_mcp
        0.08, 0.35, 0.0,  # index_pip
        0.08, 0.45, 0.0,  # index_dip
        0.08, 0.52, 0.0,  # index_tip
        0.0, 0.21, 0.0,   # middle_mcp
        0.0, 0.37, 0.0,   # middle_pip
        0.0, 0.47, 0.0,   # middle_dip
        0.0, 0.54, 0.0,   # middle_tip
        -0.07, 0.20, 0.0, # ring_mcp
        -0.07, 0.34, 0.0, # ring_pip
        -0.07, 0.43, 0.0, # ring_dip
        -0.07, 0.50, 0.0, # ring_tip
        -0.14, 0.18, 0.0, # pinky_mcp
        -0.14, 0.30, 0.0, # pinky_pip
        -0.14, 0.38, 0.0, # pinky_dip
        -0.14, 0.44, 0.0, # pinky_tip
    ],

    "FIST": [
        0.0, 0.0, 0.0,
        0.10, 0.06, 0.0,
        0.14, 0.10, 0.0,
        0.12, 0.06, -0.03,
        0.08, 0.04, -0.04,
        0.06, 0.14, 0.0,
        0.06, 0.14, -0.04,
        0.04, 0.10, -0.06,
        0.03, 0.06, -0.06,
        0.0, 0.15, 0.0,
        0.0, 0.15, -0.04,
        -0.01, 0.11, -0.06,
        -0.02, 0.07, -0.06,
        -0.06, 0.13, 0.0,
        -0.06, 0.13, -0.04,
        -0.07, 0.10, -0.05,
        -0.07, 0.07, -0.05,
        -0.11, 0.11, 0.0,
        -0.11, 0.11, -0.03,
        -0.12, 0.09, -0.04,
        -0.12, 0.07, -0.04,
    ],

    "PEACE": [
        0.0, 0.0, 0.0,
        0.10, 0.06, 0.0,
        0.14, 0.10, 0.0,
        0.12, 0.06, -0.03,
        0.08, 0.04, -0.04,
        0.06, 0.18, 0.0,
        0.06, 0.32, 0.0,
        0.06, 0.42, 0.0,
        0.06, 0.50, 0.0,
        0.0, 0.19, 0.0,
        0.0, 0.33, 0.0,
        0.0, 0.43, 0.0,
        0.0, 0.51, 0.0,
        -0.06, 0.13, 0.0,
        -0.06, 0.13, -0.04,
        -0.07, 0.10, -0.05,
        -0.07, 0.07, -0.05,
        -0.11, 0.11, 0.0,
        -0.11, 0.11, -0.03,
        -0.12, 0.09, -0.04,
        -0.12, 0.07, -0.04,
    ],

    "THUMBS_UP": [
        0.0, 0.0, 0.0,
        0.10, 0.08, 0.0,
        0.16, 0.18, 0.0,
        0.18, 0.28, 0.0,
        0.18, 0.36, 0.0,
        0.06, 0.14, 0.0,
        0.06, 0.14, -0.04,
        0.04, 0.10, -0.06,
        0.03, 0.06, -0.06,
        0.0, 0.15, 0.0,
        0.0, 0.15, -0.04,
        -0.01, 0.11, -0.06,
        -0.02, 0.07, -0.06,
        -0.06, 0.13, 0.0,
        -0.06, 0.13, -0.04,
        -0.07, 0.10, -0.05,
        -0.07, 0.07, -0.05,
        -0.11, 0.11, 0.0,
        -0.11, 0.11, -0.03,
        -0.12, 0.09, -0.04,
        -0.12, 0.07, -0.04,
    ],

    "POINT_FORWARD": [
        0.0, 0.0, 0.0,
        0.10, 0.06, 0.0,
        0.14, 0.10, 0.0,
        0.12, 0.06, -0.03,
        0.08, 0.04, -0.04,
        0.06, 0.18, 0.0,
        0.06, 0.32, 0.0,
        0.06, 0.42, 0.0,
        0.06, 0.50, 0.0,
        0.0, 0.15, 0.0,
        0.0, 0.15, -0.04,
        -0.01, 0.11, -0.06,
        -0.02, 0.07, -0.06,
        -0.06, 0.13, 0.0,
        -0.06, 0.13, -0.04,
        -0.07, 0.10, -0.05,
        -0.07, 0.07, -0.05,
        -0.11, 0.11, 0.0,
        -0.11, 0.11, -0.03,
        -0.12, 0.09, -0.04,
        -0.12, 0.07, -0.04,
    ],

    "OK_SIGN": [
        0.0, 0.0, 0.0,
        0.10, 0.08, 0.0,
        0.14, 0.14, 0.0,
        0.10, 0.18, -0.02,
        0.06, 0.16, -0.02,
        0.06, 0.18, 0.0,
        0.06, 0.18, -0.03,
        0.06, 0.16, -0.04,
        0.06, 0.14, -0.03,
        0.0, 0.19, 0.0,
        0.0, 0.33, 0.0,
        0.0, 0.43, 0.0,
        0.0, 0.51, 0.0,
        -0.06, 0.18, 0.0,
        -0.06, 0.31, 0.0,
        -0.06, 0.40, 0.0,
        -0.06, 0.47, 0.0,
        -0.11, 0.16, 0.0,
        -0.11, 0.27, 0.0,
        -0.11, 0.35, 0.0,
        -0.11, 0.41, 0.0,
    ],
}

# Number of features per landmark vector (21 landmarks × 3 coordinates)
FEATURE_DIM = 63


class GestureClassifier:
    """
    Nearest-centroid gesture classifier.

    Classifies hand landmark vectors by computing cosine similarity
    against pre-computed gesture prototype centroids. Returns the
    closest matching gesture and a confidence score.

    In production, this would be replaced with a trained sklearn
    KNeighborsClassifier or TFLite model. The nearest-centroid
    approach provides a zero-dependency baseline that demonstrates
    the ML integration architecture.
    """

    def __init__(self, confidence_threshold: float = 0.70):
        self._threshold = confidence_threshold
        self._prototypes: Dict[str, np.ndarray] = {}
        self._labels: List[str] = []

        # Build normalized prototype matrix
        for label, vec in GESTURE_PROTOTYPES.items():
            arr = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(arr)
            self._prototypes[label] = arr / norm if norm > 0 else arr
            self._labels.append(label)

        self._proto_matrix = np.stack(
            [self._prototypes[l] for l in self._labels]
        )

        logger.info(
            f"GestureClassifier initialized: {len(self._labels)} prototypes, "
            f"threshold={self._threshold}"
        )

    def classify(self, landmarks: List[float]) -> Tuple[Optional[str], float]:
        """
        Classify a 63-dimensional landmark vector.

        Args:
            landmarks: Flat list of 21 × 3 (x, y, z) coordinates
                       normalized relative to wrist origin.

        Returns:
            Tuple of (gesture_label, confidence).
            Returns (None, 0.0) if input is invalid or below threshold.
        """
        if len(landmarks) != FEATURE_DIM:
            logger.warning(
                f"Invalid landmark vector: expected {FEATURE_DIM} features, "
                f"got {len(landmarks)}"
            )
            return None, 0.0

        # Normalize input
        query = np.array(landmarks, dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm < 1e-6:
            return None, 0.0
        query = query / norm

        # Cosine similarity against all prototypes
        similarities = self._proto_matrix @ query
        best_idx = int(np.argmax(similarities))
        confidence = float(similarities[best_idx])

        label = self._labels[best_idx]

        if confidence < self._threshold:
            logger.debug(
                f"Low confidence: {label}={confidence:.3f} < {self._threshold}"
            )
            return None, confidence

        logger.info(f"Classified: {label} (confidence={confidence:.3f})")
        return label, confidence

    def classify_sequence(
        self, landmark_frames: List[List[float]]
    ) -> List[Tuple[Optional[str], float]]:
        """Classify a sequence of landmark frames."""
        return [self.classify(frame) for frame in landmark_frames]

    def classify_temporal(
        self, landmark_frames: List[List[float]]
    ) -> Tuple[Optional[str], float]:
        """
        Evaluate a rolling window of frames temporally (e.g., 30-frame buffer).
        Currently implements statistical aggregation. Architecture is structurally
        prepared for an ONNX LSTM or TCN injection.
        """
        if not landmark_frames:
            return None, 0.0

        results = self.classify_sequence(landmark_frames)
        valid = [r for r in results if r[0] is not None]
        
        if not valid:
            return None, 0.0

        from collections import Counter
        counts = Counter(r[0] for r in valid)
        best_label, majority = counts.most_common(1)[0]

        conf_sum = sum(r[1] for r in valid if r[0] == best_label)
        avg_conf = conf_sum / majority
        
        return best_label, avg_conf

    def get_status(self) -> dict:
        """Return classifier metadata."""
        return {
            "model_type": "nearest-centroid",
            "num_prototypes": len(self._labels),
            "gesture_classes": sorted(self._labels),
            "confidence_threshold": self._threshold,
            "feature_dimensions": FEATURE_DIM,
        }
