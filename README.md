# SHIA (SignAI_OS) — AI-Powered Sign Language Communication System

> Real-time sign language ↔ speech translation, powered by edge AI and LLMs.

![Status](https://img.shields.io/badge/status-beta-orange) ![Version](https://img.shields.io/badge/version-2.1.0--beta-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.10+-yellow) ![Node](https://img.shields.io/badge/node-18+-green)

---

## 🧠 What is SHIA?

**SHIA** (**S**ign language **H**uman **I**nterface **A**I) is a full-stack application that bridges the communication gap between sign language and spoken language in real-time. It uses MediaPipe for in-browser gesture tracking, GPT-4o for grammar restructuring, and WebSocket streams for zero-latency bidirectional communication.

### Two Modes

| Mode | Direction | Flow |
|------|-----------|------|
| **Sign → Speech** | Camera → MediaPipe → Gesture Detection → Grammar AI → TTS → Speaker |
| **Speech → Sign** | Microphone → STT → Translation Engine → Sign Sequence → Screen |

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

### Backend Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Middleware  │  │  REST Routes │  │     WebSocket     │  │
│  │  • Logging   │  │  /health     │  │     /ws           │  │
│  │  • Security  │  │  /api/*      │  │                   │  │
│  │  • CORS      │  │              │  │                   │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                │                    │              │
│  ┌──────▼────────────────▼────────────────────▼──────────┐  │
│  │                   Service Layer                        │  │
│  │                                                        │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  │  │
│  │  │  Grammar   │  │ Translation  │  │   Session     │  │  │
│  │  │  Engine    │  │   Engine     │  │   Manager     │  │  │
│  │  │            │  │              │  │               │  │  │
│  │  │ • OpenAI   │  │ • OpenAI     │  │ • Track IDs   │  │  │
│  │  │ • Rules    │  │ • Vocabulary │  │ • Per-session  │  │  │
│  │  │   fallback │  │   fallback   │  │   metrics     │  │  │
│  │  └────────────┘  └──────────────┘  └───────────────┘  │  │
│  │                                                        │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  │  │
│  │  │ Connection │  │  Analytics   │  │    Config     │  │  │
│  │  │  Manager   │  │   Service    │  │    Module     │  │  │
│  │  │            │  │              │  │               │  │  │
│  │  │ • WS pool  │  │ • Latency   │  │ • .env loader │  │  │
│  │  │ • Broadcast│  │ • Uptime    │  │ • Settings    │  │  │
│  │  │ • Cleanup  │  │ • Counters  │  │ • Validation  │  │  │
│  │  └────────────┘  └──────────────┘  └───────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend (Next.js)
- **Framework:** Next.js 16 + TypeScript (App Router)
- **Styling:** Tailwind CSS v4 + Framer Motion
- **Vision AI:** MediaPipe Hands (in-browser, zero-latency)
- **Audio:** Web Speech API (STT + TTS)
- **Transport:** WebSocket (real-time bidirectional)

### Backend (FastAPI)
- **Framework:** Python FastAPI with async/await
- **Real-time:** Native WebSocket with session tracking
- **Grammar AI:** OpenAI GPT-4o (with rule-based offline fallback)
- **Translation:** Vocabulary-based + LLM-enhanced sign sequence generation
- **Middleware:** Request logging, security headers, CORS
- **Analytics:** In-memory metrics (latency, sessions, throughput)
- **Config:** Centralized settings with `.env` support

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- npm

### 1. Clone & Setup

```bash
git clone https://github.com/your-username/ai-powered-communication-system.git
cd ai-powered-communication-system
```

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

API at [http://localhost:8000](http://localhost:8000) | Docs at [http://localhost:8000/docs](http://localhost:8000/docs) | ReDoc at [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at [http://localhost:3000](http://localhost:3000)

### 4. Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENV` | No | `development` | Environment mode |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server port |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `OPENAI_API_KEY` | No | — | Enables LLM-powered grammar + translation. Falls back to rules if not set. |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `FRONTEND_URL` | No | `http://localhost:3000` | Frontend URL for CORS |
| `WS_RATE_LIMIT` | No | `20` | Max WebSocket messages per second |
| `REST_RATE_LIMIT` | No | `60` | Max REST requests per minute |

---

## 📁 Project Structure

```
ai-powered-communication-system/
├── frontend/                              # Next.js Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx                # Root layout + SEO
│   │   │   ├── page.tsx                  # Main page (pipeline ↔ UI)
│   │   │   └── globals.css              # Design system
│   │   ├── components/SignAI/
│   │   │   ├── Header.tsx               # System controls
│   │   │   ├── VisionMatrix.tsx         # Camera/tracking viewport
│   │   │   ├── TranscriptLog.tsx        # Real-time log display
│   │   │   ├── QuickActions.tsx         # Status tiles
│   │   │   └── Footer.tsx               # Footer
│   │   ├── hooks/                        # ⭐ PIPELINE LAYERS
│   │   │   ├── usePipeline.ts           # Orchestrator (wires everything)
│   │   │   ├── useWebSocket.ts          # Layer 1: Transport
│   │   │   ├── useMediaPipe.ts          # Layer 2: Vision AI
│   │   │   └── useSpeech.ts             # Layer 3: TTS + STT
│   │   ├── lib/
│   │   │   ├── types.ts                 # Core type definitions
│   │   │   └── utils.ts                 # Utility functions
│   │   └── types/
│   │       └── speech.d.ts              # Web Speech API types
│   └── package.json
│
├── backend/                               # FastAPI Backend
│   ├── app/
│   │   ├── main.py                       # Server entry + WebSocket + REST routes
│   │   ├── config.py                     # Centralized settings (.env loader)
│   │   ├── middleware.py                 # Request logging + security headers
│   │   └── services/
│   │       ├── grammar_engine.py         # Sign → Natural language (LLM + rules)
│   │       ├── translation_engine.py     # Speech → Sign sequences (LLM + vocab)
│   │       ├── connection_manager.py     # WebSocket client pool management
│   │       ├── session_manager.py        # Per-connection session tracking
│   │       └── analytics.py             # System metrics & latency tracking
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                              # Local config (gitignored)
│
└── README.md
```

---

## 🔌 API Reference

### REST Endpoints

| Method | Path | Tags | Description |
|--------|------|------|-------------|
| `GET` | `/health` | System | Server health, uptime, service states, config summary |
| `POST` | `/api/translate` | Translation | One-off text translation (sign↔speech) |
| `GET` | `/api/analytics` | Analytics | System metrics: latency, sessions, throughput |
| `GET` | `/api/vocabulary` | Translation | Complete sign language vocabulary (word → gesture) |
| `GET` | `/api/grammar-rules` | Translation | Rule-based grammar mappings (offline fallback) |
| `GET` | `/api/sessions` | System | Active WebSocket sessions with per-session stats |

> 📝 **Interactive docs** available at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger) and [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)

### REST Examples

**Health Check:**
```bash
GET /health

# Response:
{
  "status": "online",
  "version": "2.1.0-beta",
  "uptime": "2h 15m 30s",
  "services": {
    "grammar_engine": "rule-based",
    "translation_engine": "vocabulary-based",
    "active_connections": 1,
    "active_sessions": 1
  }
}
```

**Translate (Sign → Speech):**
```bash
POST /api/translate
Content-Type: application/json

{"text": "hello how you", "mode": "SIGN_TO_SPEECH"}

# Response:
{
  "translated_text": "Hello!",
  "original_text": "hello how you",
  "mode": "SIGN_TO_SPEECH",
  "confidence": 0.92,
  "processing_time_ms": 1.2
}
```

**Translate (Speech → Sign):**
```bash
POST /api/translate
Content-Type: application/json

{"text": "How are you today?", "mode": "SPEECH_TO_SIGN"}

# Response:
{
  "translated_text": "HOW → BE → POINT_FORWARD → SPELL:TODAY",
  "original_text": "How are you today?",
  "mode": "SPEECH_TO_SIGN",
  "confidence": 0.89,
  "processing_time_ms": 0.8
}
```

### WebSocket Protocol (`/ws`)

**Connection Flow:**
1. Client connects to `ws://localhost:8000/ws`
2. Server sends `session_info` with assigned session ID
3. Client sends messages, server responds in real-time
4. On disconnect, session stats are logged

**Client → Server:**
```json
{ "type": "gesture_sequence", "payload": { "gestures": ["HELLO", "HOW_ARE_YOU"] } }
{ "type": "speech_input", "payload": { "text": "Hello, how are you?" } }
{ "type": "manual_text", "payload": { "text": "some text", "mode": "SIGN_TO_SPEECH" } }
{ "type": "set_mode", "payload": { "mode": "SPEECH_TO_SIGN" } }
{ "type": "ping", "payload": {} }
```

**Server → Client:**
```json
{ "type": "session_info", "payload": { "session_id": "a1b2c3d4", "mode": "SIGN_TO_SPEECH", "server_version": "2.1.0-beta" } }
{ "type": "translation_result", "payload": { "translated_text": "Hello! How are you?", "processing_time_ms": 1.5 } }
{ "type": "sign_animation", "payload": { "sign_sequence": ["WAVE_HELLO", "HOW", "BE", "POINT_FORWARD"], "processing_time_ms": 0.8 } }
{ "type": "grammar_processed", "payload": { "original": "hello how you", "corrected": "Hello! How are you?", "latency_ms": 1.2 } }
{ "type": "mode_changed", "payload": { "mode": "SPEECH_TO_SIGN" } }
{ "type": "pong", "payload": { "timestamp": "...", "session_id": "a1b2c3d4" } }
{ "type": "error", "payload": { "message": "No gestures provided" } }
```

---

## ⚙️ Backend Services

### Grammar Engine (`grammar_engine.py`)
Converts raw sign language gesture labels into grammatically correct spoken English.

- **Primary:** OpenAI GPT-4o/4o-mini (when `OPENAI_API_KEY` is set)
- **Fallback:** 31 rule-based ASL → English mappings
- **Example:** `"hello how you"` → `"Hello! How are you?"`

### Translation Engine (`translation_engine.py`)
Converts spoken English text into sign language gesture sequences.

- **Primary:** OpenAI LLM-enhanced decomposition
- **Fallback:** 72-word vocabulary with longest-match tokenization
- **Features:** Multi-word phrase matching, fingerspelling for unknown words
- **Example:** `"Hello, how are you?"` → `["WAVE_HELLO", "HOW", "BE", "POINT_FORWARD"]`

### Session Manager (`session_manager.py`)
Tracks each WebSocket connection with a unique session ID.

- Per-session metrics: gestures sent, speeches processed, errors, duration
- Session lifecycle: create → track → remove
- Queryable via `/api/sessions`

### Analytics Service (`analytics.py`)
System-wide metrics tracking (in-memory, resets on restart).

- Translation/conversion counters
- Latency tracking with rolling window (last 500 samples)
- Per-operation latency breakdown (grammar vs. translation)
- Uptime tracking
- Queryable via `/api/analytics`

### Connection Manager (`connection_manager.py`)
Manages the WebSocket connection pool.

- Accepts/removes connections
- Broadcast support (send to all clients)
- Targeted messaging (send to specific client)
- Auto-cleanup of dead connections

### Middleware (`middleware.py`)
- **RequestLoggingMiddleware:** Logs method, path, status, and response time for every request
- **SecurityHeadersMiddleware:** Adds `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, etc.

### Config (`config.py`)
- Loads `.env` file via `python-dotenv`
- Provides typed access to all settings
- Configures structured logging at startup

---

## 🎯 Design Philosophy

- **Privacy First:** MediaPipe runs entirely in-browser — video never leaves the device
- **Offline Capable:** Rule-based grammar engine + vocabulary translation work without API keys
- **Zero Latency:** Edge compute via WASM + Web Speech API
- **Graceful Degradation:** Every layer has a fallback:
  - No MediaPipe? → Simulation mode
  - No OpenAI? → Rule-based engine
  - No WebSocket? → Offline TTS
- **Accessible:** Terminal-inspired UI with high contrast, keyboard navigable
- **Observable:** Built-in analytics, session tracking, and request logging

---

## 🔧 Development

### Backend Development

```bash
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables hot-reloading on file changes.

### Frontend Development

```bash
cd frontend
npm run dev
```

### Testing the Pipeline

1. Start the backend (`uvicorn app.main:app --reload`)
2. Start the frontend (`npm run dev`)
3. Open [http://localhost:3000](http://localhost:3000)
4. Click **BOOT SYSTEM** to activate the pipeline
5. Use the camera for sign language detection, or switch to Speech → Sign mode

### Testing Without a Camera

The system runs a **demo simulation** when the backend isn't connected, automatically playing through a sample gesture sequence with grammar processing and TTS output.

---

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Analytics Dashboard
```bash
curl http://localhost:8000/api/analytics
```

Returns: uptime, total translations, active sessions, average latency, and per-session breakdowns.

### Active Sessions
```bash
curl http://localhost:8000/api/sessions
```

Returns: all connected clients with their session IDs, modes, request counts, and durations.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>SHIA</strong> — Sign language Human Interface AI<br/>
  <em>Breaking communication barriers with edge AI.</em>
</p>
