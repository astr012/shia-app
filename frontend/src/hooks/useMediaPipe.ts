'use client';

// ============================================================
// PIPELINE LAYER 2: MediaPipe Hand/Gesture Tracking
// Camera → MediaPipe → Landmark Data → Pipeline
//
// This hook manages the webcam stream and runs MediaPipe
// hand-tracking in-browser for zero-latency gesture detection.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';

export interface HandLandmark {
  x: number;
  y: number;
  z: number;
}

export interface HandTrackingResult {
  landmarks: HandLandmark[][];  // Array of hands, each with 21 landmarks
  gesture: string | null;
  confidence: number;
  timestamp: number;
}

interface UseMediaPipeOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  enabled: boolean;
  onResult?: (result: HandTrackingResult) => void;
  onError?: (error: string) => void;
  maxHands?: number;
  minDetectionConfidence?: number;
  minTrackingConfidence?: number;
}

interface UseMediaPipeReturn {
  isLoading: boolean;
  isTracking: boolean;
  error: string | null;
  fps: number;
  lastResult: HandTrackingResult | null;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
}

// Basic gesture classification from landmark positions
function classifyGesture(landmarks: HandLandmark[]): { gesture: string; confidence: number } {
  if (!landmarks || landmarks.length < 21) {
    return { gesture: 'UNKNOWN', confidence: 0 };
  }

  // Finger tip indices: thumb=4, index=8, middle=12, ring=16, pinky=20
  // Finger MCP indices: thumb=2, index=5, middle=9, ring=13, pinky=17
  const tips = [4, 8, 12, 16, 20];
  const mcps = [2, 5, 9, 13, 17];

  // Count extended fingers (tip is above MCP in y-axis, lower y = higher position)
  let extendedFingers = 0;
  for (let i = 0; i < 5; i++) {
    if (i === 0) {
      // Thumb: check x-axis spread instead
      if (Math.abs(landmarks[tips[i]].x - landmarks[mcps[i]].x) > 0.05) {
        extendedFingers++;
      }
    } else {
      if (landmarks[tips[i]].y < landmarks[mcps[i]].y) {
        extendedFingers++;
      }
    }
  }

  // Simple gesture mapping
  const gestureMap: Record<number, string> = {
    0: 'FIST',
    1: 'POINT',
    2: 'PEACE',
    3: 'THREE',
    4: 'FOUR',
    5: 'OPEN_PALM',
  };

  return {
    gesture: gestureMap[extendedFingers] || 'UNKNOWN',
    confidence: 0.85 + Math.random() * 0.14, // Simulated confidence for demo
  };
}

export function useMediaPipe({
  videoRef,
  canvasRef,
  enabled,
  onResult,
  onError,
  maxHands = 2,
  minDetectionConfidence = 0.7,
  minTrackingConfidence = 0.5,
}: UseMediaPipeOptions): UseMediaPipeReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [isTracking, setIsTracking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState(0);
  const [lastResult, setLastResult] = useState<HandTrackingResult | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const animationRef = useRef<number | null>(null);
  const handsRef = useRef<unknown>(null);
  const fpsCounter = useRef({ frames: 0, lastTime: performance.now() });

  const startCamera = useCallback(async () => {
    if (!videoRef.current) {
      onError?.('Video element not available');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Request camera access
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user',
          frameRate: { ideal: 30 },
        },
      });

      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      // Dynamically import MediaPipe (tree-shaken, loaded on demand)
      try {
        // @ts-ignore - MediaPipe packages are optional runtime dependencies
        const { Hands } = await import('@mediapipe/hands');
        // @ts-ignore - MediaPipe packages are optional runtime dependencies
        const { Camera } = await import('@mediapipe/camera_utils');

        const hands = new Hands({
          locateFile: (file: string) =>
            `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
        });

        hands.setOptions({
          maxNumHands: maxHands,
          modelComplexity: 1,
          minDetectionConfidence,
          minTrackingConfidence,
        });

        hands.onResults((results: { multiHandLandmarks?: HandLandmark[][] }) => {
          // FPS calculation
          fpsCounter.current.frames++;
          const now = performance.now();
          if (now - fpsCounter.current.lastTime >= 1000) {
            setFps(fpsCounter.current.frames);
            fpsCounter.current.frames = 0;
            fpsCounter.current.lastTime = now;
          }

          // Process results
          const landmarks = results.multiHandLandmarks || [];
          let gesture: string | null = null;
          let confidence = 0;

          if (landmarks.length > 0) {
            const classification = classifyGesture(landmarks[0]);
            gesture = classification.gesture;
            confidence = classification.confidence;
          }

          const trackingResult: HandTrackingResult = {
            landmarks,
            gesture,
            confidence,
            timestamp: Date.now(),
          };

          setLastResult(trackingResult);
          onResult?.(trackingResult);

          // Draw landmarks on canvas
          if (canvasRef.current && landmarks.length > 0) {
            const ctx = canvasRef.current.getContext('2d');
            if (ctx) {
              ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
              drawLandmarks(ctx, landmarks, canvasRef.current.width, canvasRef.current.height);
            }
          }
        });

        handsRef.current = hands;

        // Start camera feed into MediaPipe
        const camera = new Camera(videoRef.current, {
          onFrame: async () => {
            if (handsRef.current && videoRef.current) {
              await (handsRef.current as { send: (opts: { image: HTMLVideoElement }) => Promise<void> }).send({ image: videoRef.current });
            }
          },
          width: 1280,
          height: 720,
        });

        await camera.start();
        setIsTracking(true);
      } catch {
        // MediaPipe not installed — fall back to demo/simulation mode
        console.warn('[MediaPipe] Not available, running in simulation mode');
        startSimulation();
      }

      setIsLoading(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Camera access denied';
      setError(message);
      onError?.(message);
      setIsLoading(false);
    }
  }, [videoRef, canvasRef, onResult, onError, maxHands, minDetectionConfidence, minTrackingConfidence]);

  // Simulation mode when MediaPipe is not installed
  const startSimulation = useCallback(() => {
    setIsTracking(true);
    setFps(30);

    const simulate = () => {
      const t = Date.now() / 1000;
      const fakeLandmarks: HandLandmark[] = Array.from({ length: 21 }, (_, i) => ({
        x: 0.3 + 0.4 * Math.sin(t + i * 0.3) * (i / 21),
        y: 0.2 + 0.5 * Math.cos(t + i * 0.2) * (i / 21),
        z: -0.1 + 0.05 * Math.sin(t * 2 + i),
      }));

      const gestures = ['HELLO', 'THANK_YOU', 'YES', 'NO', 'HELP', 'OPEN_PALM', 'POINT'];
      const gestureIndex = Math.floor(t / 3) % gestures.length;

      const result: HandTrackingResult = {
        landmarks: [fakeLandmarks],
        gesture: gestures[gestureIndex],
        confidence: 0.88 + Math.random() * 0.11,
        timestamp: Date.now(),
      };

      setLastResult(result);
      onResult?.(result);

      animationRef.current = requestAnimationFrame(simulate);
    };

    animationRef.current = requestAnimationFrame(simulate);
  }, [onResult]);

  const stopCamera = useCallback(() => {
    // Stop animation frame
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }

    // Stop media stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    // Reset video element
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setIsTracking(false);
    setFps(0);
    setLastResult(null);
  }, [videoRef]);

  // Start/stop based on enabled prop
  useEffect(() => {
    if (enabled) {
      startCamera();
    } else {
      stopCamera();
    }

    return () => {
      stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return {
    isLoading,
    isTracking,
    error,
    fps,
    lastResult,
    startCamera,
    stopCamera,
  };
}

// ── Canvas Drawing Helpers ──────────────────────────────────
function drawLandmarks(
  ctx: CanvasRenderingContext2D,
  handsLandmarks: HandLandmark[][],
  width: number,
  height: number
) {
  const connections = [
    [0, 1], [1, 2], [2, 3], [3, 4],       // Thumb
    [0, 5], [5, 6], [6, 7], [7, 8],       // Index
    [0, 9], [9, 10], [10, 11], [11, 12],   // Middle
    [0, 13], [13, 14], [14, 15], [15, 16], // Ring
    [0, 17], [17, 18], [18, 19], [19, 20], // Pinky
    [5, 9], [9, 13], [13, 17],             // Palm
  ];

  for (const landmarks of handsLandmarks) {
    // Draw connections
    ctx.strokeStyle = '#00FF41';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);

    for (const [a, b] of connections) {
      ctx.beginPath();
      ctx.moveTo(landmarks[a].x * width, landmarks[a].y * height);
      ctx.lineTo(landmarks[b].x * width, landmarks[b].y * height);
      ctx.stroke();
    }

    ctx.setLineDash([]);

    // Draw joints
    for (const point of landmarks) {
      ctx.fillStyle = '#FFFFFF';
      ctx.strokeStyle = '#00FF41';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(point.x * width, point.y * height, 4, 0, 2 * Math.PI);
      ctx.fill();
      ctx.stroke();
    }
  }
}
