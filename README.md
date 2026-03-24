# SHIA (SignAI_OS) — AI-Powered Sign Language Communication System

> Real-time sign language ↔ speech translation, powered by edge AI and LLMs.

![Status](https://img.shields.io/badge/status-beta-orange) ![Version](https://img.shields.io/badge/version-2.2.0--beta-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.10+-yellow) ![Node](https://img.shields.io/badge/node-18+-green) ![Tests](https://img.shields.io/badge/tests-75%20passing-brightgreen) ![Docker](https://img.shields.io/badge/docker-compose-blue)

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
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │    Middleware     │  │  REST Routes │  │     WebSocket     │  │
│  │  • Request ID    │  │  /health     │  │     /ws           │  │
│  │  • Rate Limit    │  │  /api/*      │  │  • Heartbeat      │  │
│  │  • Logging       │  │  /dashboard  │  │  • Rate limited   │  │
│  │  • Security      │  │              │  │                   │  │
│  │  • CORS          │  │              │  │                   │  │
│  └──────┬───────────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                     │                    │              │
│  ┌──────▼─────────────────────▼────────────────────▼──────────┐  │
│  │                     Service Layer                           │  │
│  │                                                             │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐      │  │
│  │  │  Grammar   │  │ Translation  │  │   Session     │      │  │
│  │  │  Engine    │  │   Engine     │  │   Manager     │      │  │
│  │  │ • OpenAI   │  │ • OpenAI     │  │ • Track IDs   │      │  │
│  │  │ • Rules    │  │ • Vocabulary │  │ • Per-session  │      │  │
│  │  │   fallback │  │   fallback   │  │   metrics     │      │  │
│  │  └────────────┘  └──────────────┘  └───────────────┘      │  │
│  │                                                             │  │
│  │  ┌────────────┐  ┌──────────────┐  ┌───────────────┐      │  │
│  │  │ Translation│  │    Rate      │  │  Analytics    │      │  │
│  │  │   Cache    │  │   Limiter    │  │   Service     │      │  │
│  │  │ • LRU      │  │ • Token     │  │ • Latency     │      │  │
│  │  │ • TTL      │  │   Bucket    │  │ • Uptime      │      │  │
│  │  │ • Hit/miss │  │ • Per-IP    │  │ • Counters    │      │  │
│  │  └────────────┘  └──────────────┘  └───────────────┘      │  │
│  │                                                             │  │
│  │  ┌────────────┐  ┌──────────────┐                          │  │
│  │  │ Connection │  │    Config    │                          │  │
│  │  │  Manager   │  │   Module    │                          │  │
│  │  │ • WS pool  │  │ • .env      │                          │  │
│  │  │ • Broadcast│  │ • Settings  │                          │  │
│  │  │ • Cleanup  │  │ • Logging   │                          │  │
│  │  └────────────┘  └──────────────┘                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Exception Handling & Observability              │  │
│  │  • Global exception handler (structured JSON errors)        │  │
│  │  • HTTP exception handler (400, 404, 422 → JSON)            │  │
│  │  • X-Request-ID tracking on every request                   │  │
│  │  • X-Response-Time header                                   │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### Frontend (Next.js)
- **Framework:** Next.js 16 + TypeScript (App Router)
- **Styling:** Tailwind CSS v4 + Framer Motion
- **Vision AI:** MediaPipe Hands (in-browser, zero-latency)
- **Audio:** Web Speech API (STT + TTS)
- **Transport:** WebSocket (real-time bidirectional)
- **Pages:** Main app (`/`) + System Dashboard (`/dashboard`)

### Backend (FastAPI)
- **Framework:** Python FastAPI with async/await
- **Real-time:** Native WebSocket with session tracking + heartbeats
- **Grammar AI:** OpenAI GPT-4o (with rule-based offline fallback)
- **Translation:** Vocabulary-based + LLM-enhanced sign sequence generation
- **Caching:** LRU translation cache with TTL expiry (avoids repeated LLM calls)
- **Rate Limiting:** Token bucket per-IP (REST) + per-client (WebSocket)
- **Middleware:** Request ID tracking, rate limiting, logging, security headers, CORS
- **Error Handling:** Global exception handler with structured JSON responses
- **Analytics:** In-memory metrics (latency, sessions, throughput)
- **Testing:** 61 tests (pytest + pytest-asyncio + httpx)
- **Config:** Centralized settings with `.env` support

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- npm

### 1. Clone & Setup

```bash
git clone https://github.com/astr012/shia-app.git
cd shia-app
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

### 4. Docker (One-Command)

```bash
# Start both frontend + backend with Docker Compose
docker compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### 5. Run Tests

```bash
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -v
```

> 75 tests covering all services, REST endpoints, WebSocket pipeline, and middleware

### 6. Environment Variables

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

---

## 📁 Project Structure

```
ai-powered-communication-system/
├── frontend/                              # Next.js Application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx                # Root layout + SEO
│   │   │   ├── page.tsx                  # Main page (pipeline ↔ UI)
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx             # 📊 System Dashboard
│   │   │   └── globals.css              # Design system
│   │   ├── components/SignAI/
│   │   │   ├── Header.tsx               # System controls + nav
│   │   │   ├── VisionMatrix.tsx         # Camera/tracking viewport
│   │   │   ├── TranscriptLog.tsx        # Real-time log display
│   │   │   ├── SignPlayer.tsx           # 🆕 Sign token animation player
│   │   │   ├── QuickActions.tsx         # Status tiles
│   │   │   └── Footer.tsx               # Footer
│   │   ├── hooks/                        # ⭐ PIPELINE LAYERS
│   │   │   ├── usePipeline.ts           # Orchestrator (wires everything)
│   │   │   ├── useWebSocket.ts          # Layer 1: Transport
│   │   │   ├── useMediaPipe.ts          # Layer 2: Vision AI
│   │   │   ├── useServerHealth.ts       # Layer 4: Health polling
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
│   │   ├── middleware.py                 # Request ID, rate limit, logging, security
│   │   └── services/
│   │       ├── grammar_engine.py         # Sign → Natural language (LLM + rules)
│   │       ├── translation_engine.py     # Speech → Sign sequences (LLM + vocab)
│   │       ├── connection_manager.py     # WebSocket client pool management
│   │       ├── session_manager.py        # Per-connection session tracking
│   │       ├── analytics.py             # System metrics & latency tracking
│   │       ├── cache.py                 # 🆕 LRU translation cache with TTL
│   │       └── rate_limiter.py          # 🆕 Token bucket rate limiter
│   ├── tests/                            # 🧪 Test Suite (75 tests)
│   │   ├── test_grammar_engine.py       # Grammar engine tests (10)
│   │   ├── test_translation_engine.py   # Translation engine tests (10)
│   │   ├── test_cache.py               # Cache tests (13)
│   │   ├── test_rate_limiter.py         # Rate limiter tests (7)
│   │   ├── test_api.py                  # REST API endpoint tests (13)
│   │   ├── test_middleware.py           # Middleware + error handler tests (8)
│   │   └── test_websocket.py           # 🆕 WebSocket pipeline tests (14)
│   ├── Dockerfile                        # 🐳 Backend container
│   ├── pytest.ini                        # Test configuration
│   ├── requirements.txt
│   ├── .env.example
│   └── .env                              # Local config (gitignored)
│
├── docker-compose.yml                     # 🐳 One-command deployment
└── README.md
```

---

## 🔌 API Reference

### REST Endpoints

| Method | Path | Tags | Description |
|--------|------|------|-------------|
| `GET` | `/health` | System | Server health, uptime, service states, config summary |
| `POST` | `/api/translate` | Translation | One-off text translation (sign↔speech) |
| `GET` | `/api/analytics` | Analytics | System metrics: latency, sessions, throughput, cache, rate limiter |
| `GET` | `/api/vocabulary` | Translation | Complete sign language vocabulary (word → gesture) |
| `GET` | `/api/grammar-rules` | Translation | Rule-based grammar mappings (offline fallback) |
| `GET` | `/api/sessions` | System | Active WebSocket sessions with per-session stats |
| `GET` | `/api/cache` | System | Cache statistics (entries, hit rate, TTL) |
| `DELETE` | `/api/cache` | System | Clear translation cache |

> 📝 **Interactive docs** available at [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger) and [http://localhost:8000/redoc](http://localhost:8000/redoc) (ReDoc)

### Response Headers

Every response includes:
- `X-Request-ID` — Unique request identifier (for tracing)
- `X-Response-Time` — Server processing time
- `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection` — Security headers

### REST Examples

**Health Check:**
```bash
curl http://localhost:8000/health

# Response:
{
  "status": "online",
  "version": "2.2.0-beta",
  "uptime": "2h 15m 30s",
  "services": {
    "grammar_engine": "rule-based",
    "translation_engine": "vocabulary-based",
    "active_connections": 1,
    "active_sessions": 1
  },
  "cache": { "entries": 5, "hit_rate_pct": 75.0 },
  "rate_limiter": { "active_clients": 2, "total_denied": 0 }
}
```

**Translate (Sign → Speech):**
```bash
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "hello how you", "mode": "SIGN_TO_SPEECH"}'

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
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "How are you today?", "mode": "SPEECH_TO_SIGN"}'

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
3. Server starts heartbeat pings every 30 seconds
4. Client sends messages, server responds in real-time
5. Rate limiting: max 20 messages/second per client
6. On disconnect, session stats are logged

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
{ "type": "session_info", "payload": { "session_id": "a1b2c3d4", "mode": "SIGN_TO_SPEECH", "server_version": "2.2.0-beta" } }
{ "type": "translation_result", "payload": { "translated_text": "Hello! How are you?", "processing_time_ms": 1.5, "cached": false } }
{ "type": "sign_animation", "payload": { "sign_sequence": ["WAVE_HELLO", "HOW", "BE", "POINT_FORWARD"], "processing_time_ms": 0.8 } }
{ "type": "grammar_processed", "payload": { "original": "hello how you", "corrected": "Hello! How are you?", "latency_ms": 1.2 } }
{ "type": "mode_changed", "payload": { "mode": "SPEECH_TO_SIGN" } }
{ "type": "heartbeat", "payload": { "timestamp": "...", "session_id": "a1b2c3d4" } }
{ "type": "pong", "payload": { "timestamp": "...", "session_id": "a1b2c3d4" } }
{ "type": "rate_limited", "payload": { "message": "Rate limit exceeded. Max 20 msg/s." } }
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

### Translation Cache (`cache.py`)
LRU cache with TTL for avoiding repeated LLM/processing calls.

- **Max size:** 256 entries (configurable)
- **TTL:** 1 hour (configurable)
- **Separate namespaces:** Grammar corrections and sign translations
- **Stats:** Tracks hits, misses, and hit rate percentage
- **Clearable:** Via `DELETE /api/cache`

### Rate Limiter (`rate_limiter.py`)
Token bucket algorithm for per-client throttling.

- **WebSocket:** 20 msg/s per client (configurable)
- **REST API:** 30 req/s per IP, burst capacity 60
- **Exempt:** `/health`, `/docs`, `/redoc` endpoints
- **Response:** `429 Too Many Requests` with `Retry-After` header

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
Four middleware layers (processed in order):

1. **RequestIDMiddleware:** Assigns `X-Request-ID` (auto UUID or client-provided)
2. **RateLimitMiddleware:** Per-IP REST API throttling
3. **RequestLoggingMiddleware:** Logs `[req_id] METHOD /path → status (Xms)`
4. **SecurityHeadersMiddleware:** Security headers on all responses

### Error Handling
- **Global exception handler:** Catches unhandled errors → `{"error": "internal_server_error", "message": "...", "request_id": "..."}`
- **HTTP exception handler:** Structured JSON for 400/404/422/etc errors
- **Rate limit errors:** `429` with `Retry-After` header and structured body

### Config (`config.py`)
- Loads `.env` file via `python-dotenv`
- Provides typed access to all settings
- Configures structured logging at startup

---

## 📊 System Dashboard

Access the live system dashboard at [http://localhost:3000/dashboard](http://localhost:3000/dashboard).

**Features:**
- Real-time system status and uptime
- Translation and error counters
- Cache hit rate and capacity (with clear button)
- Active WebSocket session list
- Auto-refreshing every 8 seconds
- Deployment-aware (shows instructions on Vercel)

---

## 🧪 Testing

### Run All Tests

```bash
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -v
```

### Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_grammar_engine.py` | 10 | Rule matching, case handling, partial match, empty input, gestures |
| `test_translation_engine.py` | 10 | Word/phrase translation, skip words, vocabulary data |
| `test_cache.py` | 13 | LRU eviction, TTL expiry, stats tracking, clear |
| `test_rate_limiter.py` | 7 | Token bucket, per-client isolation, stale cleanup |
| `test_api.py` | 13 | All REST endpoints (health, translate, vocab, cache, analytics) |
| `test_middleware.py` | 8 | Rate limiting, request ID tracking, error responses |
| `test_websocket.py` | 14 | **End-to-end pipeline:** sign→speech, speech→sign, session lifecycle, manual routing, error handling |
| **Total** | **75** | **All passing ✅** |

---

## 🎯 Design Philosophy

- **Privacy First:** MediaPipe runs entirely in-browser — video never leaves the device
- **Offline Capable:** Rule-based grammar engine + vocabulary translation work without API keys
- **Zero Latency:** Edge compute via WASM + Web Speech API
- **Graceful Degradation:** Every layer has a fallback:
  - No MediaPipe? → Simulation mode
  - No OpenAI? → Rule-based engine
  - No WebSocket? → Offline TTS
  - No backend on Vercel? → Dashboard shows deployment instructions
- **Production Ready:** Rate limiting, caching, error handling, request tracing
- **Accessible:** Terminal-inspired UI with high contrast, keyboard navigable
- **Observable:** Built-in analytics, dashboard, session tracking, and structured logging
- **Tested:** 61 unit + integration tests covering all services and endpoints

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
6. Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard) to monitor the system

### Testing Without a Camera

The system runs a **demo simulation** when the backend isn't connected, automatically playing through a sample gesture sequence with grammar processing and TTS output.

---

## 🔒 Security

| Measure | Implementation | Location |
|---------|---------------|----------|
| **Rate Limiting** | Token bucket per-IP (REST: 30 req/s) + per-client (WS: 20 msg/s) | `middleware.py`, `rate_limiter.py` |
| **CORS** | Configurable `ALLOWED_ORIGINS` via env, credentials support | `main.py` (CORSMiddleware) |
| **Security Headers** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy` | `middleware.py` (SecurityHeadersMiddleware) |
| **Input Validation** | Pydantic models validate all REST request bodies (mode enum, text non-empty) | `main.py` (TranslateRequest model) |
| **XSS Prevention** | React auto-escapes all rendered output, no `dangerouslySetInnerHTML` | All frontend components |
| **CSRF Protection** | API is stateless (no cookies/sessions), CORS restricts origins | `main.py` |
| **Request Tracing** | Unique `X-Request-ID` on every request for audit trail | `middleware.py` (RequestIDMiddleware) |
| **Error Handling** | Global exception handler — never leaks stack traces to client | `main.py` (global_exception_handler) |
| **No SQL** | No database — no SQL injection surface | Architecture choice |
| **No Passwords** | No user accounts — no password storage needed | Architecture choice |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>SHIA</strong> — Sign language Human Interface AI<br/>
  <em>Breaking communication barriers with edge AI.</em>
</p>
