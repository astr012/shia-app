# SignAI_OS — AI-Powered Sign Language Communication System

> Real-time sign language to speech and speech to sign language translation, powered by edge AI.

![Status](https://img.shields.io/badge/status-beta-orange) ![Version](https://img.shields.io/badge/version-2.0.4--beta-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## 🏗️ Architecture

```
Camera/Mic (Frontend) → MediaPipe (Tracks Gestures) → FastAPI (Grammar AI) → Speaker/Screen (Output)
```

### Pipeline Flow

```
┌───────────────┐    ┌───────────────┐    ┌────────────────┐
│  Camera/Mic   │───▶│   MediaPipe/  │───▶│   WebSocket    │
│  (Input)      │    │   STT Engine  │    │   Transport    │
└───────────────┘    └───────────────┘    └───────┬────────┘
                                                  │
                                                  ▼
                                          ┌───────────────┐
                                          │  FastAPI       │
                                          │  (Grammar AI)  │
                                          └───────┬───────┘
                                                  │
                                                  ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Speaker/     │◀───│   TTS Engine  │◀───│   WebSocket   │
│  Screen       │    │   / Sign Anim │    │   Response    │
└───────────────┘    └───────────────┘    └───────────────┘
```

### Two Modes

| Mode | Direction | Flow |
|------|-----------|------|
| **Sign → Speech** | Camera → MediaPipe → Gesture Detection → Grammar AI → TTS → Speaker |
| **Speech → Sign** | Microphone → STT → Translation Engine → Sign Sequence → Screen |

---

## 🛠️ Tech Stack

### Frontend (Next.js)
- **Framework:** Next.js 16 + TypeScript (App Router)
- **Styling:** Tailwind CSS v4 + Framer Motion
- **Vision AI:** MediaPipe Hands (in-browser, zero-latency)
- **Audio:** Web Speech API (STT + TTS)
- **Transport:** WebSocket (real-time)

### Backend (FastAPI)
- **Framework:** Python FastAPI
- **Real-time:** Native WebSocket support
- **Grammar AI:** OpenAI GPT-4o (with rule-based offline fallback)
- **Translation:** Vocabulary-based + LLM-enhanced sign sequence generation

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- npm

### 1. Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at [http://localhost:3000](http://localhost:3000)

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
cp .env.example .env        # Configure your API keys

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API at [http://localhost:8000](http://localhost:8000) | Docs at [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | Enables LLM-powered grammar correction. Falls back to rules if not set. |
| `OPENAI_MODEL` | No | Model to use (default: `gpt-4o-mini`) |
| `FRONTEND_URL` | No | For CORS (default: `http://localhost:3000`) |

---

## 📁 Project Structure

```
ai-powered-communication-system/
├── frontend/                          # Next.js Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # Root layout + SEO
│   │   │   ├── page.tsx               # Main page (pipeline ↔ UI)
│   │   │   └── globals.css            # Design system
│   │   ├── components/SignAI/
│   │   │   ├── Header.tsx             # System controls
│   │   │   ├── VisionMatrix.tsx       # Camera/tracking viewport
│   │   │   ├── TranscriptLog.tsx      # Real-time log display
│   │   │   ├── QuickActions.tsx       # Status tiles
│   │   │   └── Footer.tsx             # Footer
│   │   ├── hooks/                     # ⭐ PIPELINE LAYERS
│   │   │   ├── usePipeline.ts         # Orchestrator (wires everything)
│   │   │   ├── useWebSocket.ts        # Layer 1: Transport
│   │   │   ├── useMediaPipe.ts        # Layer 2: Vision AI
│   │   │   └── useSpeech.ts           # Layer 3: TTS + STT
│   │   ├── lib/
│   │   │   ├── types.ts               # Core type definitions
│   │   │   └── utils.ts               # Utility functions
│   │   └── types/
│   │       └── speech.d.ts            # Web Speech API types
│   └── package.json
│
├── backend/                           # FastAPI Backend
│   ├── app/
│   │   ├── main.py                    # Server + WebSocket endpoint
│   │   └── services/
│   │       ├── connection_manager.py  # WebSocket client management
│   │       ├── grammar_engine.py      # Sign → Natural language (LLM)
│   │       └── translation_engine.py  # Speech → Sign sequences
│   ├── requirements.txt
│   └── .env.example
│
└── README.md
```

---

## 🔌 API Reference

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | System health check |
| `POST` | `/api/translate` | One-off text translation |

### WebSocket Protocol (`/ws`)

**Client → Server:**
```json
{ "type": "gesture_sequence", "payload": { "gestures": ["HELLO", "HOW_ARE_YOU"] } }
{ "type": "speech_input", "payload": { "text": "Hello, how are you?" } }
{ "type": "manual_text", "payload": { "text": "some text", "mode": "SIGN_TO_SPEECH" } }
```

**Server → Client:**
```json
{ "type": "translation_result", "payload": { "translated_text": "Hello! How are you?" } }
{ "type": "sign_animation", "payload": { "sign_sequence": ["WAVE_HELLO", "HOW", "BE", "POINT_FORWARD"] } }
{ "type": "grammar_processed", "payload": { "original": "hello how you", "corrected": "Hello! How are you?" } }
```

---

## 🎯 Design Philosophy

- **Privacy First:** MediaPipe runs entirely in-browser — video never leaves the device
- **Offline Capable:** Rule-based grammar engine works without API keys
- **Zero Latency:** Edge compute via WASM + Web Speech API
- **Accessible:** Terminal-inspired UI with high contrast, keyboard navigable
- **Graceful Degradation:** Every layer has a fallback (no MediaPipe? simulation mode. No OpenAI? rules-based. No WebSocket? offline TTS.)
