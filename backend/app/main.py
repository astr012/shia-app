# ============================================================
# SignAI_OS — FastAPI Backend
# Main Application Entry Point
#
# Pipeline: WebSocket ← → Grammar AI ← → Translation Engine
# ============================================================

import os
import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from app.services.grammar_engine import GrammarEngine
from app.services.translation_engine import TranslationEngine
from app.services.connection_manager import ConnectionManager

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("signai")

# ── Lifespan ─────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("🟢 SignAI_OS Backend starting...")
    logger.info(f"   Grammar Engine: {'OpenAI' if os.getenv('OPENAI_API_KEY') else 'Rule-based (fallback)'}")
    logger.info(f"   Environment: {os.getenv('ENV', 'development')}")
    yield
    logger.info("🔴 SignAI_OS Backend shutting down...")

# ── App ──────────────────────────────────────────────────────
app = FastAPI(
    title="SignAI_OS API",
    description="AI-powered sign language communication backend",
    version="2.0.4-beta",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Services ─────────────────────────────────────────────────
manager = ConnectionManager()
grammar_engine = GrammarEngine()
translation_engine = TranslationEngine()

# ── REST Endpoints ───────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    services: dict

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check endpoint."""
    return HealthResponse(
        status="online",
        version="2.0.4-beta",
        timestamp=datetime.utcnow().isoformat(),
        services={
            "grammar_engine": grammar_engine.get_status(),
            "translation_engine": translation_engine.get_status(),
            "active_connections": manager.active_count(),
        },
    )

class TranslateRequest(BaseModel):
    text: str
    mode: str  # 'SIGN_TO_SPEECH' or 'SPEECH_TO_SIGN'
    language: Optional[str] = "en"

class TranslateResponse(BaseModel):
    translated_text: str
    original_text: str
    mode: str
    confidence: float

@app.post("/api/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """REST endpoint for one-off translations (non-realtime)."""
    try:
        if request.mode == "SIGN_TO_SPEECH":
            # Process gesture labels into natural speech
            corrected = await grammar_engine.process(request.text)
            return TranslateResponse(
                translated_text=corrected,
                original_text=request.text,
                mode=request.mode,
                confidence=0.92,
            )
        else:
            # Process speech into sign sequence
            sign_sequence = await translation_engine.speech_to_sign(request.text)
            return TranslateResponse(
                translated_text=" → ".join(sign_sequence),
                original_text=request.text,
                mode=request.mode,
                confidence=0.89,
            )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── WebSocket Endpoint (Real-time Pipeline) ──────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main real-time pipeline endpoint.
    
    Incoming message types:
      - gesture_sequence: Array of detected gestures → grammar AI → speech text
      - speech_input: Spoken text → sign language sequence
      - manual_text: Manual text input → process based on mode
    
    Outgoing message types:
      - translation_result: Final translated text
      - sign_animation: Sign language animation sequence
      - grammar_processed: Grammar correction details
      - error: Error details
    """
    await manager.connect(websocket)
    logger.info(f"Client connected. Active: {manager.active_count()}")

    try:
        while True:
            raw = await websocket.receive_text()
            
            try:
                message = json.loads(raw)
                msg_type = message.get("type")
                payload = message.get("payload", {})
                
                logger.info(f"[WS] Received: {msg_type}")

                if msg_type == "gesture_sequence":
                    await handle_gesture_sequence(websocket, payload)

                elif msg_type == "speech_input":
                    await handle_speech_input(websocket, payload)

                elif msg_type == "manual_text":
                    await handle_manual_text(websocket, payload)

                elif msg_type == "ping":
                    await send_ws(websocket, "pong", {"timestamp": datetime.utcnow().isoformat()})

                else:
                    await send_ws(websocket, "error", {"message": f"Unknown type: {msg_type}"})

            except json.JSONDecodeError:
                await send_ws(websocket, "error", {"message": "Invalid JSON"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Client disconnected. Active: {manager.active_count()}")


# ── Pipeline Handlers ────────────────────────────────────────

async def handle_gesture_sequence(ws: WebSocket, payload: dict):
    """
    SIGN → SPEECH Pipeline:
    Gesture labels → Grammar Engine (LLM) → Natural text → Send back for TTS
    """
    gestures = payload.get("gestures", [])
    if not gestures:
        await send_ws(ws, "error", {"message": "No gestures provided"})
        return

    # Step 1: Join raw gestures
    raw_text = " ".join(g.replace("_", " ").lower() for g in gestures)
    logger.info(f"[Pipeline] Raw gesture text: {raw_text}")

    # Step 2: Grammar correction / natural language restructuring
    corrected_text = await grammar_engine.process(raw_text)
    logger.info(f"[Pipeline] Corrected text: {corrected_text}")

    # Send grammar processing result
    await send_ws(ws, "grammar_processed", {
        "original": raw_text,
        "corrected": corrected_text,
    })

    # Step 3: Send final translation
    await send_ws(ws, "translation_result", {
        "translated_text": corrected_text,
        "source_gesture": " → ".join(gestures),
    })


async def handle_speech_input(ws: WebSocket, payload: dict):
    """
    SPEECH → SIGN Pipeline:
    Spoken text → Translation Engine → Sign language sequence
    """
    text = payload.get("text", "")
    if not text:
        await send_ws(ws, "error", {"message": "No text provided"})
        return

    logger.info(f"[Pipeline] Speech input: {text}")

    # Convert speech to sign sequence
    sign_sequence = await translation_engine.speech_to_sign(text)
    logger.info(f"[Pipeline] Sign sequence: {sign_sequence}")

    await send_ws(ws, "sign_animation", {
        "sign_sequence": sign_sequence,
        "source_text": text,
    })


async def handle_manual_text(ws: WebSocket, payload: dict):
    """Handle manual text input — route based on mode."""
    text = payload.get("text", "")
    mode = payload.get("mode", "SIGN_TO_SPEECH")

    if mode == "SIGN_TO_SPEECH":
        corrected = await grammar_engine.process(text)
        await send_ws(ws, "translation_result", {
            "translated_text": corrected,
            "source_gesture": "MANUAL",
        })
    else:
        sign_sequence = await translation_engine.speech_to_sign(text)
        await send_ws(ws, "sign_animation", {
            "sign_sequence": sign_sequence,
            "source_text": text,
        })


# ── Helpers ──────────────────────────────────────────────────

async def send_ws(ws: WebSocket, msg_type: str, payload: dict):
    """Send a structured WebSocket message."""
    await ws.send_json({
        "type": msg_type,
        "payload": payload,
        "timestamp": datetime.utcnow().timestamp(),
    })
