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

// ── MediaPipe Type Contracts (CDN-loaded, no @types available) ──

interface VisionState {
  hands: { x: number; y: number; z: number }[][];
  pose: ({ x: number; y: number; z: number } & { visibility?: number })[] | null;
  face: { x: number; y: number; z: number }[][];
}

interface MediaPipeInstance {
  initialize(): Promise<void>;
  setOptions(options: Record<string, unknown>): void;
  onResults(callback: (results: Record<string, unknown>) => void): void;
  send(input: { image: HTMLVideoElement }): Promise<void>;
}

interface MediaPipeCamera {
  start(): Promise<void>;
  stop(): void;
}

interface MediaPipeCameraConstructor {
  new (video: HTMLVideoElement, options: { onFrame: () => Promise<void>; width: number; height: number }): MediaPipeCamera;
}

// --- MediaPipe Global Singleton ---
// Instantiating Hands multiple times (e.g., in React StrictMode) causes
// Emscripten memory corruption and XHR fetch aborts. A singleton prevents this.
let globalHandsInstance: MediaPipeInstance | null = null;
let globalPoseInstance: MediaPipeInstance | null = null;
let globalFaceMeshInstance: MediaPipeInstance | null = null;
let globalCameraClass: MediaPipeCameraConstructor | null = null;
let mediaPipeInitPromise: Promise<void> | null = null;
let activeOnResultsCallback: ((results: VisionState) => void) | null = null;
const activeVisionState: VisionState = { hands: [], pose: null, face: [] };

async function initMediaPipe() {
  if (globalHandsInstance && globalPoseInstance && globalFaceMeshInstance && globalCameraClass) return;
  if (!mediaPipeInitPromise) {
    mediaPipeInitPromise = (async () => {
      const { Hands } = await import('@mediapipe/hands');
      const { Pose } = await import('@mediapipe/pose');
      const { FaceMesh } = await import('@mediapipe/face_mesh');
      const { Camera } = await import('@mediapipe/camera_utils');
      
      globalHandsInstance = new Hands({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/${file}`,
      }) as unknown as MediaPipeInstance;
      await globalHandsInstance.initialize();

      globalPoseInstance = new Pose({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose@0.5.1675469404/${file}`,
      }) as unknown as MediaPipeInstance;
      await globalPoseInstance.initialize();

      globalFaceMeshInstance = new FaceMesh({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh@0.4.1633559619/${file}`,
      }) as unknown as MediaPipeInstance;
      await globalFaceMeshInstance.initialize();

      globalCameraClass = Camera as unknown as MediaPipeCameraConstructor;
      
      // Route results to whatever component is currently active
      globalPoseInstance.onResults((results: Record<string, unknown>) => {
        activeVisionState.pose = (results.poseLandmarks as VisionState['pose']) || null;
      });
      globalFaceMeshInstance.onResults((results: Record<string, unknown>) => {
        activeVisionState.face = (results.multiFaceLandmarks as VisionState['face']) || [];
      });
      globalHandsInstance.onResults((results: Record<string, unknown>) => {
        activeVisionState.hands = (results.multiHandLandmarks as VisionState['hands']) || [];
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
  localStream: MediaStream | null;
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
  private lastEmitted: string | null = null;

  constructor(windowSize: number = 3) {
    this.windowSize = windowSize;
  }

  /**
   * Push a gesture into the stabilizer.
   * Returns the stabilized gesture or null if uncertain.
   *
   * Three fast-paths:
   * 1. High-confidence bypass (caller signals via pushWithConfidence)
   * 2. Transition detection — new gesture differs from last emitted → emit immediately
   * 3. Majority vote at 50% threshold
   */
  push(gesture: string, confidence?: number): string | null {
    // Fast-path: high-confidence detection bypasses the window
    if (confidence !== undefined && confidence > 0.88) {
      this.lastEmitted = gesture;
      this.buffer = [gesture]; // reset buffer to the new gesture
      return gesture;
    }

    this.buffer.push(gesture);
    if (this.buffer.length > this.windowSize) {
      this.buffer.shift();
    }

    // Transition detection: if new gesture differs from last emitted and
    // appears at least twice in the buffer, emit immediately
    if (this.lastEmitted !== null && gesture !== this.lastEmitted) {
      const countNew = this.buffer.filter(g => g === gesture).length;
      if (countNew >= 2) {
        this.lastEmitted = gesture;
        return gesture;
      }
    }

    // Majority vote — need buffer full
    if (this.buffer.length < this.windowSize) return null;

    const counts: Record<string, number> = {};
    for (const g of this.buffer) {
      counts[g] = (counts[g] || 0) + 1;
    }

    // 50% majority (down from 60%)
    const threshold = Math.ceil(this.windowSize * 0.5);
    for (const [g, count] of Object.entries(counts)) {
      if (count >= threshold) {
        this.lastEmitted = g;
        return g;
      }
    }

    return null;
  }

  clear() {
    this.buffer = [];
    this.lastEmitted = null;
  }
}

// ── Geometry Helpers (rotation-invariant) ─────────────────────

function dist(a: HandLandmark, b: HandLandmark): number {
  return Math.hypot(a.x - b.x, a.y - b.y, (a.z ?? 0) - (b.z ?? 0));
}

/** Compute angle (degrees) at vertex B given triangle A-B-C */
function angleDeg(a: HandLandmark, b: HandLandmark, c: HandLandmark): number {
  const ba = { x: a.x - b.x, y: a.y - b.y, z: (a.z ?? 0) - (b.z ?? 0) };
  const bc = { x: c.x - b.x, y: c.y - b.y, z: (c.z ?? 0) - (b.z ?? 0) };
  const dot = ba.x * bc.x + ba.y * bc.y + ba.z * bc.z;
  const magBA = Math.hypot(ba.x, ba.y, ba.z);
  const magBC = Math.hypot(bc.x, bc.y, bc.z);
  if (magBA < 1e-8 || magBC < 1e-8) return 0;
  const cosAngle = Math.max(-1, Math.min(1, dot / (magBA * magBC)));
  return Math.acos(cosAngle) * (180 / Math.PI);
}

/**
 * Determine if a finger is extended using the angle at PIP joint.
 * Straight finger ≈ 180°, curled finger ≈ 60-90°.
 * Threshold: > 155° = extended (works regardless of hand orientation).
 */
function isFingerExtended(
  landmarks: HandLandmark[],
  mcp: number,
  pip: number,
  dip: number,
  tip: number,
): boolean {
  const pipAngle = angleDeg(landmarks[mcp], landmarks[pip], landmarks[dip]);
  const dipAngle = angleDeg(landmarks[pip], landmarks[dip], landmarks[tip]);
  // Both joints need to be relatively straight
  return pipAngle > 155 && dipAngle > 140;
}

/**
 * Determine if thumb is extended using abduction from palm.
 * Uses angle at CMC (landmark 2) with wrist and MCP as reference,
 * plus tip-to-index_mcp distance relative to palm size.
 * Works for both left and right hands.
 */
function isThumbExtended(landmarks: HandLandmark[], palmSize: number): boolean {
  // Angle at MCP joint (landmark 2): wrist(0) - thumb_mcp(2) - thumb_ip(3)
  const mcpAngle = angleDeg(landmarks[0], landmarks[2], landmarks[3]);
  // Angle at IP joint: thumb_mcp(2) - thumb_ip(3) - thumb_tip(4)
  const ipAngle = angleDeg(landmarks[2], landmarks[3], landmarks[4]);

  // Distance from thumb tip to index MCP (relative to palm)
  const thumbAbduction = dist(landmarks[4], landmarks[5]) / (palmSize || 0.001);

  // Thumb is extended if the joints aren't tightly curled AND it's abducted from the palm
  return (mcpAngle > 120 || ipAngle > 140) && thumbAbduction > 0.7;
}

// ── Gesture Classification (rotation-invariant, angle-based) ──

function classifyGesture(landmarks: HandLandmark[]): { gesture: string | null; confidence: number } {
  if (!landmarks || landmarks.length < 21) {
    return { gesture: null, confidence: 0 };
  }

  const wrist = landmarks[0];
  const palmSize = dist(wrist, landmarks[9]); // wrist to middle MCP

  // Guard: hand too small / too far → unreliable
  if (palmSize < 0.01) {
    return { gesture: null, confidence: 0 };
  }

  // ── Finger state detection (angle-based, orientation-independent) ──
  const thumb = isThumbExtended(landmarks, palmSize);
  const index = isFingerExtended(landmarks, 5, 6, 7, 8);
  const middle = isFingerExtended(landmarks, 9, 10, 11, 12);
  const ring = isFingerExtended(landmarks, 13, 14, 15, 16);
  const pinky = isFingerExtended(landmarks, 17, 18, 19, 20);

  const fingerStates = [thumb, index, middle, ring, pinky];
  const extendedCount = fingerStates.filter(Boolean).length;

  // Palm-relative distances (scale-invariant)
  const thumbIndexDist = dist(landmarks[4], landmarks[8]) / palmSize;
  const indexMiddleDist = dist(landmarks[8], landmarks[12]) / palmSize;
  const indexPinkyDist = dist(landmarks[8], landmarks[20]) / palmSize;

  // Thumb tip direction relative to thumb MCP (for thumbs up/down detection)
  // Using wrist-relative vertical: compare thumb tip to thumb CMC
  const thumbVertical = landmarks[2].y - landmarks[4].y; // positive = tip above CMC

  // ── Specific gesture patterns (ordered by specificity) ──

  // LETTER_A: fist with thumb to the side (thumb extended, all others curled)
  if (!index && !middle && !ring && !pinky && thumb) {
    // Check thumb tip is roughly beside the fist, not above/below
    const thumbIPAngle = angleDeg(landmarks[2], landmarks[3], landmarks[4]);
    if (thumbIPAngle > 130 && Math.abs(thumbVertical) < palmSize * 0.5) {
      return { gesture: 'LETTER_A', confidence: 0.87 };
    }
  }

  // THUMBS_UP / THUMBS_DOWN: only thumb extended
  if (thumb && !index && !middle && !ring && !pinky) {
    if (thumbVertical > palmSize * 0.2) {
      return { gesture: 'THUMBS_UP', confidence: 0.93 };
    }
    if (thumbVertical < -palmSize * 0.2) {
      return { gesture: 'THUMBS_DOWN', confidence: 0.90 };
    }
    // Thumb to the side → still a thumb gesture
    return { gesture: 'THUMBS_UP', confidence: 0.82 };
  }

  // OK_SIGN: thumb+index tips close, other fingers extended
  if (thumbIndexDist < 0.35 && middle && ring) {
    return { gesture: 'OK_SIGN', confidence: 0.91 };
  }

  // PINCH: thumb+index close, others curled
  if (thumbIndexDist < 0.35 && !middle && !ring && !pinky) {
    return { gesture: 'PINCH', confidence: 0.88 };
  }

  // I_LOVE_YOU: thumb + index + pinky (ASL ILY)
  if (thumb && index && !middle && !ring && pinky) {
    return { gesture: 'I_LOVE_YOU', confidence: 0.90 };
  }

  // HORNS: index + pinky, no thumb
  if (!thumb && index && !middle && !ring && pinky) {
    return { gesture: 'HORNS', confidence: 0.87 };
  }

  // CALL_ME: thumb + pinky only
  if (thumb && !index && !middle && !ring && pinky) {
    return { gesture: 'CALL_ME', confidence: 0.88 };
  }

  // POINT: only index extended
  if (!thumb && index && !middle && !ring && !pinky) {
    // Direction from index MCP to tip (rotation-aware)
    const dx = landmarks[8].x - landmarks[5].x;
    const dy = landmarks[8].y - landmarks[5].y;
    const angle = Math.atan2(dy, dx) * (180 / Math.PI);
    if (angle < -60) return { gesture: 'POINT_UP', confidence: 0.92 };
    if (angle > 60) return { gesture: 'POINT_DOWN', confidence: 0.90 };
    return { gesture: 'POINT', confidence: 0.92 };
  }

  // PEACE / V / TWO: index + middle extended
  if (index && middle && !ring && !pinky) {
    if (indexMiddleDist > 0.45) {
      return { gesture: 'PEACE', confidence: 0.92 };
    }
    return { gesture: 'TWO', confidence: 0.87 };
  }

  // THREE: index + middle + ring
  if (index && middle && ring && !pinky && !thumb) {
    return { gesture: 'THREE', confidence: 0.88 };
  }

  // FOUR: all fingers except thumb
  if (index && middle && ring && pinky && !thumb) {
    return { gesture: 'FOUR', confidence: 0.89 };
  }

  // OPEN_PALM / HELLO: all five extended
  if (extendedCount === 5) {
    if (indexPinkyDist > palmSize * 0.8) {
      return { gesture: 'OPEN_PALM', confidence: 0.93 };
    }
    return { gesture: 'HELLO', confidence: 0.90 };
  }

  // FIST: everything curled
  if (extendedCount === 0) {
    return { gesture: 'FIST', confidence: 0.92 };
  }

  // SNAP: thumb + middle only
  if (thumb && !index && middle && !ring && !pinky) {
    return { gesture: 'SNAP', confidence: 0.84 };
  }

  // W_SIGN: thumb + index + middle
  if (thumb && index && middle && !ring && !pinky) {
    return { gesture: 'W_SIGN', confidence: 0.85 };
  }

  // No confident match — return null (NOT "UNKNOWN" at 0.6)
  return { gesture: null, confidence: 0 };
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
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);

  // Detect device capability once
  const [deviceProfile] = useState(() => detectDeviceProfile());

  const streamRef = useRef<MediaStream | null>(null);
  const animationRef = useRef<number | null>(null);
  const handsRef = useRef<MediaPipeInstance | null>(null);
  const poseRef = useRef<MediaPipeInstance | null>(null);
  const faceMeshRef = useRef<MediaPipeInstance | null>(null);
  const cameraRef = useRef<MediaPipeCamera | null>(null);
  const fpsCounter = useRef({ frames: 0, lastTime: performance.now(), lowFpsTicks: 0 });
  const frameCount = useRef(0);
  const stabilizerRef = useRef(new GestureStabilizer(deviceProfile.smoothingWindow));
  const shedModelsRef = useRef(false);

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
      setLocalStream(stream);
      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      // Dynamically import MediaPipe using the singleton to avoid Emscripten crashes
      try {
        await initMediaPipe();
        const hands = globalHandsInstance!;
        const pose = globalPoseInstance!;
        const faceMesh = globalFaceMeshInstance!;
        const Camera = globalCameraClass!;

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
        activeOnResultsCallback = (visionState: VisionState) => {
          // Frame skipping for low-end devices
          frameCount.current++;
          if (frameCount.current % deviceProfile.frameSkip !== 0) return;

          // FPS calculation & Model Shedding
          fpsCounter.current.frames++;
          const now = performance.now();
          if (now - fpsCounter.current.lastTime >= 1000) {
            const currentFps = fpsCounter.current.frames * deviceProfile.frameSkip;
            setFps(currentFps);
            
            // Thermal/FPS Shedding: If FPS drops below 8 for 5 seconds, shed Pose model
            if (currentFps < 8) {
              fpsCounter.current.lowFpsTicks++;
              if (fpsCounter.current.lowFpsTicks >= 5 && !shedModelsRef.current) {
                console.warn('[MediaPipe] Thermal/FPS drop detected. Shedding Pose model to recover performance.');
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
            // Skip null classifications (no confident match)
            if (classification.gesture !== null) {
              // Stabilize gesture — pass confidence for high-confidence bypass
              const stable = stabilizerRef.current.push(classification.gesture, classification.confidence);
              gesture = stable;
              confidence = classification.confidence;
            }
          }

          const trackingResult: HandTrackingResult = {
            landmarks,
            poseLandmarks: visionState.pose ?? undefined,
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
              if (handsRef.current) promises.push(handsRef.current.send({ image: videoRef.current }));
              if (poseRef.current && !shedModelsRef.current) promises.push(poseRef.current.send({ image: videoRef.current }));
              if (faceMeshRef.current) promises.push(faceMeshRef.current.send({ image: videoRef.current }));
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
  }, [videoRef, canvasRef, onResult, onError, maxHands, minDetectionConfidence, minTrackingConfidence, deviceProfile, startSimulation]);



  const stopCamera = useCallback(() => {
    // Stop animation frame
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }

    // Stop MediaPipe camera
    if (cameraRef.current) {
      cameraRef.current.stop();
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
      setLocalStream(null);
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
    localStream,
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

