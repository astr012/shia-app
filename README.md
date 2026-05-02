# SignAI (SHIA) 

A high-performance, bidirectional translation system converting gesture-based language to speech, and speech to gesture-based language, utilizing edge-based computer vision and asynchronous inference routing.

## Core Features

*   **Real-time Processing**: Sub-second latency execution via WebSocket streaming multiplexers.
*   **Sign-to-Speech**: Edge camera ingress → MediaPipe CV boundary → Grammar LLM integration → Web Audio synthesis.
*   **Speech-to-Sign**: Edge microphone ingress → Web Speech recognition → Translation inference → React UI rendering.
*   **Deterministic Reliability**: Automated invocation of static-rule dictionaries during stochastic engine failure states.
*   **Edge Isolation**: Complete zero-egress processing for computer vision matrix mapping utilizing WebAssembly.

## Architecture Blueprint

```mermaid
graph LR
    Client[React Client / Edge CV] <-->|WebSocket Connection| Gateway[FastAPI Gateway]
    Gateway --> Cache[LRU Cache Registry]
    Cache -- Miss Event --> Probabilistic[Stochastic Model: GPT-4o]
    Probabilistic -- Connection Exception --> Deterministic[Static Core Engine]
```

## Infrastructure Stack

| Domain | Technology Framework | Responsibility Scope |
| --- | --- | --- |
| **Client** | Next.js 16 | UI Layer, Isolated React Hooks, Edge CV Pipeline |
| **Transport**| FastAPI (Python 3.10) | Asynchronous I/O routing, rate-limiter, WebSocket hub |
| **Inference**| MediaPipe / GPT-4o | Coordinate spatial calculation & intent translation |

## Directory Architecture

```text
ai-powered-communication-system/
├── backend/                  # FastAPI asynchronous inference gateway
│   ├── app/                  # Application routing & logic bounds
│   ├── tests/                # Deterministic unit execution matrix
│   ├── Dockerfile            # Microservice container definition
│   └── requirements.txt      # Python dependency tree
├── frontend/                 # Client UI & Edge computer vision layer
│   ├── src/                  # Next.js 16 interface & isolated state
│   ├── public/               # Static presentation assets
│   ├── Dockerfile            # Client container definition
│   └── package.json          # Node dependency tree
├── .agents/                  # Autonomous intelligence schemas
├── Architecture.md           # Deep-dive system topology
└── docker-compose.yml        # Multi-container orchestration logic
```

## Initialization Protocols

### Requirements
*   Docker & Docker Compose.
*   Valid OpenAI API Key.

### Configuration
Define environment variables in `backend/.env` before invocation:
```env
OPENAI_API_KEY=your_api_key_string
OPENAI_MODEL=gpt-4o-mini
ENV=development
```

### Containerized Execution
```bash
git clone https://github.com/astr012/shia-app.git
cd shia-app
docker compose up --build
```
* **Frontend**: `http://localhost:3000`
* **API Root**: `http://localhost:8000`

## Maintainers constraints
Engineered per strict enterprise execution parameters: High algorithmic isolation, immutable component logic separation, and strict adherence to SOLID integration concepts.