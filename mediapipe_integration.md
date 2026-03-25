# MediaPipe Integration Documentation

## Overview
The `ai-powered-communication-system` leverages **MediaPipe** (Pipeline Layer 2) for zero-latency, in-browser gesture tracking. It acts as the primary sensory input for recognizing sign language gestures directly on the edge. By performing the heavy lifting on the client's side, this architecture minimizes egress bandwidth, preserves data privacy (as raw video feeds are never transmitted), and significantly reduces translation latency.

This document details the robust implementation encapsulated within the `useMediaPipe.ts` hook (`frontend/src/hooks/useMediaPipe.ts`).

---

## Core Operational Architecture

The MediaPipe stack in this application is divided into several architectural components to ensure performance and reliability across wildly differing end-user devices.

### 1. Device Profile Discovery & Adaptive Scaling
To support hardware with varying capacities (ranging from legacy mobile phones to modern desktop workstations), the system utilizes **Adaptive Performance Generation**. Upon initialization, the hook queries browser hardware APIs (`navigator.hardwareConcurrency` for CPU cores and `navigator.deviceMemory` for RAM). 

Devices are dynamically bucketed into a performance tier:
- **Low Tier:** Analyzes every 3rd frame (15 fps ideal) at 320x240 resolution using the `lite` complexity model. Uses a narrow 2-frame window for gesture stabilization.
- **Mid Tier:** Analyzes every 2nd frame at 640x480 resolution using the `lite` complexity model.
- **High Tier:** Analyzes every frame (30 fps ideal) at 640x480 resolution using the `full` complexity model. Uses a wide 4-frame window for maximum gesture stability.

*Engineering Benefit:* Prevents thermal throttling on constrained devices while ensuring zero dropped frames.

### 2. The Gesture Stabilizer
Raw coordinate point-clouds inherently produce jitter. This creates rapidly fluctuating gesture output streams (e.g., alternating between "FIST" and "POINT" over a split second) which confuses the backend LLM engine.

The `GestureStabilizer` acts as a deterministic sliding-window data filter.
- **Operation:** It stores sequentially emitted gestures into a buffer bounded by the tier's `smoothingWindow` size.
- **Consensus:** A gesture string is only released to the parent application if it holds at least a 60% majority consensus across the temporal window.

### 3. Gesture Classification Engine
Instead of relying exclusively on opaque classification machine-learning models, the system uses a deterministic front-line processor that evaluates raw Cartesian coordinates (`x, y, z`). The algorithm calculates relationships across the array's 21 landmarks:
- Identifies active fingers by comparing fingertip position (`tips` array) against intermediate joints (`pips` and `mcps`).
- Thumb evaluation explicitly measures x-axis expansion to detect horizontal spreading.

**Supported Primary Vocabularies:**
- Action states: `THUMBS_UP`, `THUMBS_DOWN`, `POINT`, `CALL_ME`, `I_LOVE_YOU`, `OK_SIGN`.
- Quantity-based states (0-5 extended fingers): `FIST`, `PEACE`, `THREE`, `FOUR`, `OPEN_PALM`.

### 4. Dynamic Loading and The Simulator Fallback
To minimize the Initial Load Time and initial Javascript bundle tax, both `@mediapipe/hands` and `@mediapipe/camera_utils` are fetched asynchronously (`import()`). 

In environments where MediaPipe crashes—such as aggressive ad-blockers, organizational firewalls rejecting CDN payloads, or rejected webcam permissions—the hook catches the fault and triggers `startSimulation()`. 
- **The Simulator:** Emits a continuous stream of smoothly rotating, mathematically generated (using sinusoidal algorithms) mock-landmarks. This capability allows engineers to develop, style, and debug the frontend/backend systems without repeatedly performing the gestures themselves.

---

## API Surface (useMediaPipe Hook)

Consumers (React functional components) interface with the pipeline strictly via the exposed `UseMediaPipeReturn` interface. Hook integration looks like this:

```typescript
import { useMediaPipe } from '@/hooks/useMediaPipe';

const {
  isLoading,      // Indicates if models are currently fetching from CDNs
  isTracking,     // Boolean flag indicating active camera/feed classification
  error,          // Camera or MediaPipe initialization faults 
  fps,            // Telemetry metric: Actively calculated Frames Per Second
  lastResult,     // Hydrated object containing 21 landmarks array and gesture string
  startCamera,    // Unbound initialization trigger
  stopCamera,     // Memory-safe teardown routines
  deviceTier      // Diagnostic string indicating detected client hardware profile
} = useMediaPipe({
  videoRef,       // HTMLVideoElement Ref
  canvasRef,      // HTMLCanvasElement Ref (For rendering the geometric skeleton)
  enabled: true,  // Auto-start initialization boolean
  onResult: (result) => console.log(result.gesture, result.confidence)
});
```

### Visual Output Processing
The hook inherently provides canvas utilities (`drawLandmarks`) designed to translate the structural bounds of the hand. Translating vectors between adjacent landmarks (e.g., thumb elements `[0,1]..[3,4]` shifting down to palm nodes), developers can provide immersive neon overlays reflecting the tracked skeleton instantly back to the end user.

---

## Tuning and Engineering Guidelines
When optimizing for higher-fidelity recognition or registering new complex hand signs within `useMediaPipe.ts`, bear in mind:

1. **Object Multiplication:** Refrain from expanding `maxHands` above 1 without significant testing. Latency and jitter compound linearly for every secondary tracked limb.
2. **Confidence Windows:** Decreasing `minDetectionConfidence` (default `0.6`) below `0.5` causes environmental artifacts (textures, faces) to trigger false classification loops.
3. **Telemetry UI:** Expose the `deviceTier` variable in standard usage. When end-users experience "low accuracy", visualizing that they are operating exclusively in the `low` tier prevents erroneous bug reports regarding the foundational translation systems.
