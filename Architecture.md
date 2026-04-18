# SHIA (SignAI_OS) System Architecture

| Parameter | Specification |
| --- | --- |
| Application Profile | Bidirectional edge-translation interface. |
| Architecture Mode | Asynchronous, event-driven stream processing. |
| Core Objective | Sub-second latency translation utilizing decoupled logic layers. |

## Operational Matrices

| Mode | Ingress | Boundary Processing | Central Inference | Egress |
| --- | --- | --- | --- | --- |
| Sign-to-Speech | Local Camera | MediaPipe Edge-CV | Grammar Orchestrator | Native Web Audio TTS |
| Speech-to-Sign | Local Microphone | Web Speech API | Translation Orchestrator | React Canvas UI |

## Core System Architecture

```mermaid
graph TD
    subgraph Edge Client [React Presentation Layer]
        UI[Stateless Components]
        Hooks[Isolated State/Logic]
        CV[MediaPipe WebAssembly]
    end
    
    subgraph Transport [Boundary Access]
        WS[WebSocket Stream]
        REST[HTTP/REST]
    end
    
    subgraph Gateway [FastAPI Asynchronous Backend]
        MW[Telemetry & Header Middleware]
        Limiter[Token Bucket Rate Limiter]
        G_Engine[Grammar Engine]
        T_Engine[Translation Engine]
        Cache[In-Memory LRU Cache]
    end
    
    subgraph External Dependencies [Inference Vectors]
        LLM[OpenAI GPT-4o]
        Dict[Static Rule Dictionary]
    end

    UI --> Hooks
    Hooks --> CV
    CV --> WS
    Hooks --> REST
    WS --> MW
    REST --> MW
    MW --> Limiter
    Limiter --> G_Engine
    Limiter --> T_Engine
    G_Engine --> Cache
    T_Engine --> Cache
    Cache -- Miss --> LLM
    LLM -- Network/Auth Exception --> Dict
```

## Sequential Execution: Sign-to-Speech Flow

```mermaid
sequenceDiagram
    participant E as Edge Client (React)
    participant C as Computer Vision (MediaPipe)
    participant N as Transport (WebSocket)
    participant S as Server Application (FastAPI)
    participant M as Model Selector (Logic)

    E->>C: Push Video Frame Buffer
    C-->>E: Return Pose Landmarks
    E->>N: Emit Coordinate Vector Matrix
    N->>S: Ingress Payload (UUID Injected)
    S->>S: Consult Transport Rate Limiter
    S->>M: Process Vector Matrix
    alt API Valid & Latency Within Bounds
        M-->>S: GPT-4o Analyzed Output
    else Network Interruption
        M-->>S: Deterministic Rule-Based Output
    end
    S-->>N: Construct Output Schema
    N-->>E: Read Operation
    E->>E: Audio Synthesis Execution
```

## Inference Pipeline Determinism

```mermaid
stateDiagram-v2
    state "Ingress Payload" as In
    state "LRU Key-Value Cache" as Cache
    state "Stochastic Inference (OpenAI)" as Stochastic
    state "Deterministic Mapping (Rules)" as RuleBased
    state "Egress Serializer" as Out
    
    In --> Cache: Query Vector Hash
    Cache --> Out: Cache Hit (t < 1ms)
    Cache --> Stochastic: Cache Miss
    
    Stochastic --> Out: Response Valid
    Stochastic --> RuleBased: HTTP Error / Timeout Extracted
    RuleBased --> Out: Formatted Sequence Map
    
    Out --> Cache: Asynchronous Write
```

## Infrastructure Matrix

| Layer | Environment | Technology | Responsibility Constraint |
| --- | --- | --- | --- |
| Client | Node 18+ | Next.js 16 | Segregated logic/presentation, zero data egress CV. |
| Server | Python 3.10+ | FastAPI | Asynchronous IO strict compliance, event loop management. |
| Processing | Native | MediaPipe | Offloaded spatial compute. |
| Storage | Memory | Dict-based Hash | TTL constraints, external dependency mitigation. |

## Deployment Operations

### Environment Configuration

| Variable | Fallback Default | Domain Specificity |
| --- | --- | --- |
| `ENV` | `development` | Operating context. |
| `FRONTEND_URL` | `http://localhost:3000` | Strict CORS configuration matrix. |
| `HOST` | `0.0.0.0` | Socket assignment vector. |
| `PORT` | `8000` | Application bind port. |
| `LOG_LEVEL` | `INFO` | STDOUT/STDERR threshold. |
| `OPENAI_API_KEY` | `null` | Requires defined credential for stochastic logic. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Parameter allocation target. |
| `WS_RATE_LIMIT`| `20` | Volumetric constraints (messages/second). |

### Base Instantiation

```bash
git clone https://github.com/astr012/shia-app.git
cd shia-app

# Backend Routine
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend Routine
cd ../frontend
npm install
npm run dev

# Container Routine
cd ../
docker compose up --build
```

## Interface Protocols

### HTTP/REST Matrix

| Vector | End-node | Telemetry Profile | Execution Pattern |
| --- | --- | --- | --- |
| `GET` | `/health` | Diagnostic | Returns system boundary status. |
| `GET` | `/api/analytics` | APM | Returns cache hit ratios & latency distribution. |
| `GET` | `/api/sessions` | APM | Maps active WebSocket handlers. |
| `GET` | `/api/vocabulary`| Static | Exposes deterministic boundary constraints. |
| `POST`| `/api/translate` | Process | Initiates synchronous pipeline. |
| `DELETE`| `/api/cache` | Command | Purges LRU dictionaries. |

### Header Boundaries
- Obligatory `X-Request-ID` propagation across all HTTP routines.
- Obligatory `X-Response-Time` insertion by response middleware.

### WebSockets (`/ws`)
- Handshake confirmation required.
- Heartbeat ping scheduled at 30,000ms intervals.
- Throttled automatically at application memory boundary.

#### Schema (Client to Server)
```json
{ "type": "gesture_sequence", "payload": { "gestures": ["GESTURE_ID"] } }
```

#### Schema (Server to Client)
```json
{ "type": "translation_result", "payload": { "translated_text": "string", "cached": boolean } }
```

## Security & Observability Operations

| Defense Variable | Methodology | Framework Node |
| --- | --- | --- |
| Exhaustion Mitigation | Token Bucket algorithms | `rate_limiter.py` |
| Execution Tracing | Immutable UUID mapping | `middleware.py` |
| Payload Verification | Pydantic strict casting | Subsystem models |
| Leakage Prevention | Client-side memory CV processing | Browser WebAssembly |
| Dependency Isolation | Deterministic engine fallbacks | `grammar_engine.py` |
| Authorization | Role-based access control (user/admin) | `auth.py` â†’ `require_role()` |
| CORS Hardening | Restricted methods + explicit header allowlist | `main.py` â†’ `CORSMiddleware` |
| CSRF Protection | Origin/Referer validation on state-changing requests | `middleware.py` â†’ `CSRFMiddleware` |
| XSS Prevention | Input sanitization + Content-Security-Policy | `translation.py` + `SecurityHeadersMiddleware` |
| SQL Injection Prevention | SQLAlchemy ORM parameterized queries (zero raw SQL) | `crud.py`, `database.py` |
| Password Policy | bcrypt hashing + configurable strength validation | `auth.py` â†’ `validate_password_strength()` |
| Transport Security | HSTS + Permissions-Policy headers (production) | `SecurityHeadersMiddleware` |
| Quality Control | 86 deterministic passing tests | `pytest` suite |
