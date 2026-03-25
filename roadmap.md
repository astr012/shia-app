# SignAI_OS (SHIA) Detailed Product Roadmap

## Overview
This document serves as the master architectural roadmap for the **SignAI_OS** project. It dictates the current implemented state and maps the future trajectories. 

For every module, an uncompromising engineering standard is enforced: Every feature must possess an actionable End-to-End (E2E) audit task, undergo full pipeline connectivity mapping, and be structurally integrated with **self-healing** and **fail-safe** architectures to eliminate bugs without human interference.

---

## Phase 1: Core Foundation (Implemented Features)

### 1. MediaPipe Edge-CV Tracking
**Status:** Implemented
**Feature Document:** `mediapipe_integration.md`
**Description:** Zero-latency client-side WebAssembly inference for real-time hand gesture tracking. Includes adaptive performance scaling based on hardware capability.
- **E2E Audit Task:** Execute Red Team Protocol targeting WASM tampering, boundary spoofing, and frame-buffer flooding. Verify that the Gesture Stabilizer rejects malformed coordinate sets.
- **Pipeline Connectivity Audit:** Analyze the boundary handoff between `useMediaPipe` (React) and the WebSocket ingress. *Identified Gap:* High-frequency micro-jitter can cause downstream WebSocket rate-limiting.
- **Self-Healing & Fail-Safe Architecture:** Implement auto-calibrating downgrade logic. If the client browser drops frames or memory spikes, the hook automatically downgrades resolution and complexity models gracefully. If MediaPipe completely crashes, it fails over to the integrated sinusoidal Simulator mode.

### 2. WebSocket Transport Layer
**Status:** Implemented
**Description:** Full-duplex persistent stream linking the React edge with the FastAPI processing gateway, incorporating strict token algorithms and 30-second heartbeats.
- **E2E Audit Task:** Perform async event-loop starvation testing. Emulate thousands of parallel corrupted session handshakes to observe degradation under DoS conditions.
- **Pipeline Connectivity Audit:** Verify Session ID (UUID) state preservation across micro network drops. *Identified Gap:* Socket disruptions currently drop translation contexts or require a hard page reload.
- **Self-Healing & Fail-Safe Architecture:** Introduce exponential back-off reconnection loops on the frontend client (`usePipeline.ts`). On the server side, implement a "circuit breaker". If connection pools surpass RAM bounds, the gateway automatically sheds idle connections and restricts new handshakes, preserving active pipelines.

### 3. Grammar Orchestrator (Gesture-to-Speech)
**Status:** Implemented
**Description:** Receives coordinate matrices to translate gestures into English language models via OpenAI GPT-4o, backed by a static dictionary mapping system.
- **E2E Audit Task:** Conduct advanced Prompt Injection audits (LLM Subversion) via poisoned gesture sequences. Attempt to leak internal prompts or trigger inference loops.
- **Pipeline Connectivity Audit:** Track boundary exceptions. Map the exact millisecond cascade when an LLM timeout triggers the exact failover to local static rules.
- **Self-Healing & Fail-Safe Architecture:** The dual-layer design is already fail-safe. To expand self-healing, implement automatic context truncation: If an inference API times out sequentially, the engine temporarily blacklists the stochastic route for 60 seconds and utilizes static logic flawlessly to ensure uninterrupted communication.

### 4. Translation Orchestrator (Speech-to-Sign)
**Status:** Implemented
**Description:** Consumes native Web Speech API audio-to-text strings, generating exact sign language sequences for visual rendering.
- **E2E Audit Task:** Evaluate logic resilience against broken English phrases, rapid muttering, or homophone collision. Test string extraction constraints.
- **Pipeline Connectivity Audit:** Analyze the synchronization gap where returned sign sequences do not match the animation execution speed of the frontend graphics component.
- **Self-Healing & Fail-Safe Architecture:** Implement payload normalization pipelines. If the system receives non-parsable or heavily garbled speech, it triggers an automatic "clarification logic" loop (requesting repetition) rather than crashing the rendering canvas with blank sequences.

### 5. In-Memory LRU Cache & Rate Limiting
**Status:** Implemented
**Description:** Telemetry tracked token-bucket limiters paired with a strict LRU translation cache to offload third-party LLM costs.
- **E2E Audit Task:** Perform cache poisoning attacks. Verify that a maliciously constructed query string cannot taint the shared namespace for subsequent clients.
- **Pipeline Connectivity Audit:** *Identified Gap:* Under multi-process deployment (Gunicorn/Uvicorn workers > 1), in-memory hashes are isolated per worker, breaking global rate limits and reducing cache hits.
- **Self-Healing & Fail-Safe Architecture:** Abstract state management to a unified Redis cluster. Crucially, if the Redis instance crashes, the system must detect the socket failure and instantly execute a self-healing rollback to local localized in-memory maps without interrupting traffic.

---

## Phase 2: Advanced Capabilities (Future Implementations)

### 6. Multi-Modal Vision Processing Expansion
**Status:** Planned
**Description:** Upgrading MediaPipe algorithms beyond `Hands` to incorporate `Pose` and `Face Mesh`. Essential for capturing the crucial facial grammar of ASL.
- **E2E Audit Task:** Memory boundary testing. Evaluate VRAM / RAM spikes during concurrent multi-model executions on standardized mid-tier hardware.
- **Pipeline Connectivity Audit:** Ensure the primary WebSocket ingress `Pydantic` models possess elastic validation structures to handle facial arrays without rejecting standard legacy hand structs.
- **Self-Healing & Fail-Safe Architecture:** Implement predictive thermal/frame monitoring. If the user's device begins to lag (FPS drops under 10), the application heals the stream by automatically shedding the Face Mesh and Pose models, alerting the user while persisting solely on lightweight Hands tracking.

### 7. Core Database & Identity Architecture
**Status:** Planned
**Description:** Persistent user profiling via PostgreSQL mapping regional dialects (e.g., BSL vs ASL) and bespoke conversational dictionaries.
- **E2E Audit Task:** Formulate SQL injection matrices and execute JWT token manipulation assessments mimicking unauthorized administrative privilege escalation.
- **Pipeline Connectivity Audit:** Investigate how customized user dictionaries securely merge with the global inference context without polluting the core logic trees.
- **Self-Healing & Fail-Safe Architecture:** Database agnostic redundancy. The edge client mirrors user profiles via `IndexedDB`. If the primary PostgreSQL cluster isolates due to network failures, the web client seamlessly loads its local state without halting translation abilities, syncing upstream upon restoration.

### 8. WebRTC Peer-to-Peer Visual Conferencing
**Status:** Planned
**Description:** Direct P2P secure video calls displaying live gesture-translated subtitles across remote clients.
- **E2E Audit Task:** STUN/TURN server leak audits. Protect P2P clients from exposing raw IP data to malicious endpoints.
- **Pipeline Connectivity Audit:** WebRTC datachannel flows circumvent the traditional WebSocket FastAPI boundary. Ensure the translation orchestration syncs properly via RTCDataChannels.
- **Self-Healing & Fail-Safe Architecture:** "Hole-Punching" state awareness. If symmetric NAT routers block the primary WebRTC pathways, the application architecture instantly recognizes the failure and reroutes video data frames transparently over a secure fallback TURN server or standard WebSocket relay.

## Phase 3: Production & Autonomous Expansion (Future Exploration)

### 9. 3D WebGL Avatar Rendering (Speech-to-Sign)
**Status:** Brainstorming
**Description:** Replacing static 2D vector outputs with real-time 3D glTF/GLB models using React Three Fiber. Essential for accurate spatial grammar and facial expression tracking inherent to advanced ASL.
- **E2E Audit Task:** Shader compilation timeout audits across legacy integrated graphics processors (GPUs).
- **Pipeline Connectivity Audit:** Synchronize 60fps avatar bone manipulation with incoming LLM context chunk streams without interpolation clipping or drift.
- **Self-Healing & Fail-Safe Architecture:** WebGL Context Loss Recovery. If the client browser forcibly kills the WebGL context due to VRAM starvation, the engine isolates the component and instantly fails over to lightweight 2D CSS-based subtitle animations, alerting the user but continuing communication.

### 10. Federated Edge Training (Micro-ML)
**Status:** Brainstorming
**Description:** Extreme data privacy. The browser retrains bespoke regional gesture classifiers locally (via TensorFlow.js) without transmitting raw camera biometric data or user profiles to the FastAPI cloud.
- **E2E Audit Task:** Training-data poisoning simulation. Inject deliberately corrupted weight gradients over 100 epochs to verify if the local error-bounded model rapidly decays.
- **Pipeline Connectivity Audit:** Evaluate IndexedDB synchronization bottlenecks when committing, serializing, and rolling back gigabyte-heavy tensor weight binaries.
- **Self-Healing & Fail-Safe Architecture:** Thermal-Aware Gradient Halting. If the training compilation loop causes device frame rates to collapse or triggers thermal throttling alerts, the federated loop aborts instantly, caching partial weights to IndexedDB, and falls back to cheap static inference rules.

---

## Execution Mandate

*Before marking any feature as "Completed", the engineering team must satisfy the following pipeline requirement:*

1. Run the targeted **E2E Red Team Protocol** (`SKILL.md`).
2. Map the failure sequence using simulated load and inject crashes intentionally.
3. Validate that the **Self-Healing** routine recovers the thread within `1000ms`. 
4. Any subsystem gap preventing seamless fallback marks the feature as incomplete.
