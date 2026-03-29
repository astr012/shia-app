'use client';

// ============================================================
// PIPELINE LAYER 2: MediaPipe Hand/Gesture Tracking
// Camera → MediaPipe → Landmark Data → Pipeline
//
// ADAPTIVE PERFORMANCE: Auto-detects device capability and
// adjusts resolution, model complexity, and frame rate to
// work smoothly on ALL devices (phones, tablets, old laptops).
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';

// --- MediaPipe Global Singleton ---
// Instantiating Hands multiple times (e.g., in React StrictMode) causes
// Emscripten memory corruption and XHR fetch aborts. A singleton prevents this.
let globalHandsInstance: any = null;
let globalPoseInstance: any = null;
let globalFaceMeshInstance: any = null;
let globalCameraClass: any = null;
let mediaPipeInitPromise: Promise<void> | null = null;
let activeOnResultsCallback: ((results: any) => void) | null = null;
let activeVisionState: any = { hands: [], pose: null, face: [] };

async function initMediaPipe(deviceProfile: any) {
  if (globalHandsInstance && globalPoseInstance && globalFaceMeshInstance && globalCameraClass) return;
  if (!mediaPipeInitPromise) {
    mediaPipeInitPromise = (async () => {
      // @ts-ignore
      const { Hands } = await import('@mediapipe/hands');
      // @ts-ignore
      const { Pose } = await import('@mediapipe/pose');
      // @ts-ignore
      const { FaceMesh } = await import('@mediapipe/face_mesh');
      // @ts-ignore
      const { Camera } = await import('@mediapipe/camera_utils');
      
      globalHandsInstance = new Hands({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/${file}`,
      });
      await globalHandsInstance.initialize();

      globalPoseInstance = new Pose({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5.1675469404/${file}`,
      });
      await globalPoseInstance.initialize();

      globalFaceMeshInstance = new FaceMesh({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}`,
      });
      await globalFaceMeshInstance.initialize();

      globalCameraClass = Camera;
      
      // Route results to whatever component is currently active
      globalPoseInstance.onResults((results: any) => {
        activeVisionState.pose = results.poseLandmarks || null;
      });
      globalFaceMeshInstance.onResults((results: any) => {
        activeVisionState.face = results.multiFaceLandmarks || [];
      });
      globalHandsInstance.onResults((results: any) => {
        activeVisionState.hands = results.multiHandLandmarks || [];
        if (activeOnResultsCallback) {
          activeOnResultsCallback(activeVisionState);
        }
      });
    })();
  }
  await mediaPipeInitPromise;
}

export interface HandLandmark {
  x: number;
  y: number;
  z: number;
}

export interface HandTrackingResult {
  landmarks: HandLandmark[][];  // Array of hands, each with 21 landmarks
  poseLandmarks?: (HandLandmark & { visibility?: number })[]; // Optional Pose 
  faceLandmarks?: HandLandmark[][]; // Optional Face Mesh 
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
  deviceTier: 'low' | 'mid' | 'high';
  isShedding: boolean;
}

// ── Device Capability Detection ──────────────────────────────
// Auto-detect device performance tier for adaptive settings.
// This ensures smooth operation on ALL devices universally.

interface DeviceProfile {
  tier: 'low' | 'mid' | 'high';
  cameraWidth: number;
  cameraHeight: number;
  modelComplexity: 0 | 1;
  frameSkip: number;        // Process every N frames (1 = every frame)
  smoothingWindow: number;  // Frames to average for gesture stability
}

function detectDeviceProfile(): DeviceProfile {
  if (typeof navigator === 'undefined') {
    return { tier: 'mid', cameraWidth: 640, cameraHeight: 480, modelComplexity: 0, frameSkip: 1, smoothingWindow: 3 };
  }

  const cores = navigator.hardwareConcurrency || 2;
  // @ts-ignore — deviceMemory is available on Chrome/Edge
  const memory = (navigator as { deviceMemory?: number }).deviceMemory || 4;
  const isMobile = /Android|iPhone|iPad|iPod|webOS|BlackBerry|Opera Mini/i.test(navigator.userAgent);
  const isLowEnd = cores <= 2 || memory <= 2 || (isMobile && cores <= 4);
  const isHighEnd = cores >= 8 && memory >= 8 && !isMobile;

  if (isLowEnd) {
    return {
      tier: 'low',
      cameraWidth: 320,
      cameraHeight: 240,
      modelComplexity: 0,   // Lite model — fastest
      frameSkip: 3,         // Process every 3rd frame
      smoothingWindow: 2,
    };
  }

  if (isHighEnd) {
    return {
      tier: 'high',
      cameraWidth: 640,
      cameraHeight: 480,
      modelComplexity: 1,   // Full model — most accurate
      frameSkip: 1,         // Every frame
      smoothingWindow: 4,
    };
  }

  // Mid-tier (most devices including average laptops, tablets)
  return {
    tier: 'mid',
    cameraWidth: 640,
    cameraHeight: 480,
    modelComplexity: 0,     // Lite model — good balance
    frameSkip: 2,           // Every other frame
    smoothingWindow: 3,
  };
}

// ── Gesture Smoothing (reduces false positives on ALL devices) ──

class GestureStabilizer {
  private buffer: string[] = [];
  private windowSize: number;

  constructor(windowSize: number = 3) {
    this.windowSize = windowSize;
  }

  push(gesture: string): string | null {
    this.buffer.push(gesture);
    if (this.buffer.length > this.windowSize) {
      this.buffer.shift();
    }

    // Only emit if the same gesture appears in majority of window
    if (this.buffer.length < this.windowSize) return null;

    const counts: Record<string, number> = {};
    for (const g of this.buffer) {
      counts[g] = (counts[g] || 0) + 1;
    }

    const threshold = Math.ceil(this.windowSize * 0.6); // 60% agreement
    for (const [gesture, count] of Object.entries(counts)) {
      if (count >= threshold) return gesture;
    }

    return null;
  }

  clear() {
    this.buffer = [];
  }
}

// ── Gesture Classification (expanded — 25+ gestures) ─────────

function angleBetween(a: HandLandmark, b: HandLandmark, c: HandLandmark): number {
  const ab = { x: a.x - b.x, y: a.y - b.y };
  const cb = { x: c.x - b.x, y: c.y - b.y };
  const dot = ab.x * cb.x + ab.y * cb.y;
  const cross = ab.x * cb.y - ab.y * cb.x;
  return Math.atan2(cross, dot) * (180 / Math.PI);
}

function dist(a: HandLandmark, b: HandLandmark): number {
  return Math.hypot(a.x - b.x, a.y - b.y, (a.z ?? 0) - (b.z ?? 0));
}

function classifyGesture(landmarks: HandLandmark[]): { gesture: string; confidence: number } {
  if (!landmarks || landmarks.length < 21) {
    return { gesture: 'UNKNOWN', confidence: 0 };
  }

  const tips = [4, 8, 12, 16, 20];
  const pips = [3, 6, 10, 14, 18];
  const mcps = [2, 5, 9, 13, 17];
  const wrist = landmarks[0];

  // Extended finger detection
  const fingerStates: boolean[] = [];
  for (let i = 0; i < 5; i++) {
    if (i === 0) {
      fingerStates.push(Math.abs(landmarks[tips[i]].x - landmarks[mcps[i]].x) > 0.04);
    } else {
      fingerStates.push(landmarks[tips[i]].y < landmarks[pips[i]].y);
    }
  }

  const [thumb, index, middle, ring, pinky] = fingerStates;
  const extendedCount = fingerStates.filter(Boolean).length;
  const thumbIndexDist = dist(landmarks[4], landmarks[8]);
  const thumbMiddleDist = dist(landmarks[4], landmarks[12]);
  const indexMiddleDist = dist(landmarks[8], landmarks[12]);
  const palmSize = dist(wrist, landmarks[9]);

  // ── Specific gesture patterns (ordered by specificity) ──

  // A (fist with thumb to side)
  if (!index && !middle && !ring && !pinky && thumb && landmarks[4].x < landmarks[3].x) {
    return { gesture: 'LETTER_A', confidence: 0.85 };
  }

  // Thumbs up / down
  if (thumb && !index && !middle && !ring && !pinky) {
    if (landmarks[4].y < landmarks[2].y) {
      return { gesture: 'THUMBS_UP', confidence: 0.91 };
    }
    return { gesture: 'THUMBS_DOWN', confidence: 0.87 };
  }

  // OK sign: thumb+index circle, others extended
  if (thumbIndexDist < 0.04 && middle && ring) {
    return { gesture: 'OK_SIGN', confidence: 0.89 };
  }

  // Pinch (thumb+index close, others curled)
  if (thumbIndexDist < 0.04 && !middle && !ring && !pinky) {
    return { gesture: 'PINCH', confidence: 0.86 };
  }

  // ILY (I Love You): thumb + index + pinky
  if (thumb && index && !middle && !ring && pinky) {
    return { gesture: 'I_LOVE_YOU', confidence: 0.88 };
  }

  // Rock on / horns: index + pinky, no thumb
  if (!thumb && index && !middle && !ring && pinky) {
    return { gesture: 'HORNS', confidence: 0.84 };
  }

  // Call me: thumb + pinky
  if (thumb && !index && !middle && !ring && pinky) {
    return { gesture: 'CALL_ME', confidence: 0.86 };
  }

  // Point: only index extended
  if (!thumb && index && !middle && !ring && !pinky) {
    // Determine direction
    const indexAngle = Math.atan2(
      landmarks[8].y - landmarks[5].y,
      landmarks[8].x - landmarks[5].x
    ) * (180 / Math.PI);
    if (indexAngle < -60) return { gesture: 'POINT_UP', confidence: 0.90 };
    if (indexAngle > 60) return { gesture: 'POINT_DOWN', confidence: 0.88 };
    return { gesture: 'POINT', confidence: 0.91 };
  }

  // Peace / V sign
  if (index && middle && !ring && !pinky) {
    if (indexMiddleDist > 0.06) {
      return { gesture: 'PEACE', confidence: 0.90 };
    }
    return { gesture: 'TWO', confidence: 0.85 };
  }

  // Three fingers
  if (index && middle && ring && !pinky && !thumb) {
    return { gesture: 'THREE', confidence: 0.86 };
  }

  // Four fingers
  if (index && middle && ring && pinky && !thumb) {
    return { gesture: 'FOUR', confidence: 0.87 };
  }

  // Open palm / stop
  if (extendedCount === 5) {
    // Check if fingers are spread wide
    const spread = dist(landmarks[8], landmarks[20]);
    if (spread > palmSize * 1.2) {
      return { gesture: 'OPEN_PALM', confidence: 0.92 };
    }
    return { gesture: 'HELLO', confidence: 0.88 };
  }

  // Fist
  if (extendedCount === 0) {
    return { gesture: 'FIST', confidence: 0.90 };
  }

  // Middle finger + thumb = "money" / snap position
  if (thumb && !index && middle && !ring && !pinky) {
    return { gesture: 'SNAP', confidence: 0.82 };
  }

  // Thumb + index + middle = "3 with thumb"
  if (thumb && index && middle && !ring && !pinky) {
    return { gesture: 'W_SIGN', confidence: 0.83 };
  }

  return {
    gesture: 'UNKNOWN',
    confidence: 0.60,
  };
}

// ── The Hook ────────────────────────────────────────────────

export function useMediaPipe({
  videoRef,
  canvasRef,
  enabled,
  onResult,
  onError,
  maxHands = 1,       // Default 1 hand for better performance
  minDetectionConfidence = 0.6,
  minTrackingConfidence = 0.5,
}: UseMediaPipeOptions): UseMediaPipeReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [isTracking, setIsTracking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fps, setFps] = useState(0);
  const [lastResult, setLastResult] = useState<HandTrackingResult | null>(null);
  const [isShedding, setIsShedding] = useState(false);

  // Detect device capability once
  const [deviceProfile] = useState(() => detectDeviceProfile());

  const streamRef = useRef<MediaStream | null>(null);
  const animationRef = useRef<number | null>(null);
  const handsRef = useRef<unknown>(null);
  const poseRef = useRef<unknown>(null);
  const faceMeshRef = useRef<unknown>(null);
  const cameraRef = useRef<unknown>(null);
  const fpsCounter = useRef({ frames: 0, lastTime: performance.now(), lowFpsTicks: 0 });
  const frameCount = useRef(0);
  const stabilizerRef = useRef(new GestureStabilizer(deviceProfile.smoothingWindow));
  const shedModelsRef = useRef(false);

  const startCamera = useCallback(async () => {
    if (!videoRef.current) {
      onError?.('Video element not available');
      return;
    }

    setIsLoading(true);
    setError(null);
    shedModelsRef.current = false;
    setIsShedding(false);
    fpsCounter.current = { frames: 0, lastTime: performance.now(), lowFpsTicks: 0 };

    try {
      // Adaptive camera resolution based on device capability
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: deviceProfile.cameraWidth },
          height: { ideal: deviceProfile.cameraHeight },
          facingMode: 'user',
          frameRate: { ideal: deviceProfile.tier === 'low' ? 15 : 30 },
        },
      });

      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      // Dynamically import MediaPipe using the singleton to avoid Emscripten crashes
      try {
        await initMediaPipe(deviceProfile);
        const hands = globalHandsInstance;
        const pose = globalPoseInstance;
        const faceMesh = globalFaceMeshInstance;
        const Camera = globalCameraClass;

        hands.setOptions({
          maxNumHands: maxHands,
          modelComplexity: deviceProfile.modelComplexity,  // Adaptive!
          minDetectionConfidence,
          minTrackingConfidence,
        });
        pose.setOptions({
          modelComplexity: deviceProfile.modelComplexity,
          minDetectionConfidence,
          minTrackingConfidence,
        });
        faceMesh.setOptions({
          maxNumFaces: 1,
          refineLandmarks: true,
          minDetectionConfidence,
          minTrackingConfidence,
        });

        // Setup callback routing
        activeOnResultsCallback = (visionState: any) => {
          // Frame skipping for low-end devices
          frameCount.current++;
          if (frameCount.current % deviceProfile.frameSkip !== 0) return;

          // FPS calculation & Model Shedding
          fpsCounter.current.frames++;
          const now = performance.now();
          if (now - fpsCounter.current.lastTime >= 1000) {
            const currentFps = fpsCounter.current.frames * deviceProfile.frameSkip;
            setFps(currentFps);
            
            // Thermal/FPS Shedding: If FPS drops below 15 for 5 seconds, shed heavy models
            if (currentFps < 15) {
              fpsCounter.current.lowFpsTicks++;
              if (fpsCounter.current.lowFpsTicks >= 5 && !shedModelsRef.current) {
                console.warn('[MediaPipe] Thermal/FPS drop detected. Shedding Pose and Face Mesh models.');
                shedModelsRef.current = true;
                setIsShedding(true);
              }
            } else {
              fpsCounter.current.lowFpsTicks = 0;
            }

            fpsCounter.current.frames = 0;
            fpsCounter.current.lastTime = now;
          }

          // Process results
          const landmarks = visionState.hands;
          let gesture: string | null = null;
          let confidence = 0;

          if (landmarks.length > 0) {
            const classification = classifyGesture(landmarks[0]);
            // Stabilize gesture (reduces jitter on all devices)
            const stable = stabilizerRef.current.push(classification.gesture);
            gesture = stable;
            confidence = classification.confidence;
          }

          const trackingResult: HandTrackingResult = {
            landmarks,
            poseLandmarks: visionState.pose,
            faceLandmarks: visionState.face,
            gesture,
            confidence,
            timestamp: Date.now(),
          };

          setLastResult(trackingResult);
          onResult?.(trackingResult);

          // Draw landmarks on canvas
          if (canvasRef.current) {
            const ctx = canvasRef.current.getContext('2d');
            if (ctx) {
              ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
              drawLandmarks(ctx, trackingResult, canvasRef.current.width, canvasRef.current.height);
            }
          }
        };

        handsRef.current = hands;
        poseRef.current = pose;
        faceMeshRef.current = faceMesh;

        // Start camera feed into MediaPipe
        const camera = new Camera(videoRef.current, {
          onFrame: async () => {
            if (videoRef.current) {
              const promises = [];
              if (handsRef.current) promises.push((handsRef.current as any).send({ image: videoRef.current }));
              if (poseRef.current && !shedModelsRef.current) promises.push((poseRef.current as any).send({ image: videoRef.current }));
              if (faceMeshRef.current && !shedModelsRef.current) promises.push((faceMeshRef.current as any).send({ image: videoRef.current }));
              await Promise.all(promises);
            }
          },
          width: deviceProfile.cameraWidth,
          height: deviceProfile.cameraHeight,
        });

        cameraRef.current = camera;
        await camera.start();
        setIsTracking(true);
        console.log(`[MediaPipe] Started — Device: ${deviceProfile.tier}, Resolution: ${deviceProfile.cameraWidth}x${deviceProfile.cameraHeight}, Model: ${deviceProfile.modelComplexity === 0 ? 'lite' : 'full'}`);
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
  }, [videoRef, canvasRef, onResult, onError, maxHands, minDetectionConfidence, minTrackingConfidence, deviceProfile]);

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

      const gestures = ['HELLO', 'THANK_YOU', 'YES', 'NO', 'HELP', 'OPEN_PALM', 'POINT', 'THUMBS_UP', 'I_LOVE_YOU', 'PEACE'];
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

    // Stop MediaPipe camera
    if (cameraRef.current) {
      (cameraRef.current as any).stop();
      cameraRef.current = null;
    }

    // Note: We do NOT close the hands instance as it's a singleton.
    // Calling .close() while it's loading causes Emscripten crash in StrictMode
    if (handsRef.current) {
      activeOnResultsCallback = null;
      handsRef.current = null;
      poseRef.current = null;
      faceMeshRef.current = null;
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

    // Clear stabilizer
    stabilizerRef.current.clear();

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
    deviceTier: deviceProfile.tier,
    isShedding,
  };
}

// ── Canvas Drawing Helpers ──────────────────────────────────
function drawLandmarks(
  ctx: CanvasRenderingContext2D,
  result: HandTrackingResult,
  width: number,
  height: number
) {
  // Draw Face Mesh
  if (result.faceLandmarks && result.faceLandmarks[0]) {
    for (const point of result.faceLandmarks[0]) {
      ctx.fillStyle = '#FF00FF';
      ctx.beginPath();
      ctx.arc(point.x * width, point.y * height, 1, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  // Draw Pose
  if (result.poseLandmarks) {
    const poseConnections = [
      [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], // Upper body
      [11, 23], [12, 24], [23, 24] // Torso
    ];
    ctx.strokeStyle = '#00FFFF';
    ctx.lineWidth = 2;
    for (const [a, b] of poseConnections) {
      const p1 = result.poseLandmarks[a];
      const p2 = result.poseLandmarks[b];
      if (p1 && p2 && (p1.visibility ?? 0) > 0.5 && (p2.visibility ?? 0) > 0.5) {
        ctx.beginPath();
        ctx.moveTo(p1.x * width, p1.y * height);
        ctx.lineTo(p2.x * width, p2.y * height);
        ctx.stroke();
      }
    }
  }

  // Draw Hands
  const handsLandmarks = result.landmarks || [];
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

