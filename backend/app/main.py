# ============================================================
# SignAI_OS — FastAPI Backend
# Main Application Entry Point
#
# Pipeline: WebSocket ←→ Grammar AI ←→ Translation Engine
#
# Services:
#   - GrammarEngine:      Sign → Speech (LLM + rule-based)
#   - TranslationEngine:  Speech → Sign (LLM + vocabulary)
#   - SessionManager:     Per-connection tracking
#   - AnalyticsService:   System-wide metrics
#   - ConnectionManager:  WebSocket lifecycle
#   - TranslationCache:   LRU cache for repeated translations
#   - RateLimiter:        Token bucket per-client throttling
# ============================================================

import time
import json
import asyncio
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware, RateLimitMiddleware, RequestIDMiddleware
from app.services.grammar_engine import GrammarEngine
from app.services.translation_engine import TranslationEngine
from app.services.connection_manager import ConnectionManager
from app.services.session_manager import SessionManager
from app.services.analytics import AnalyticsService
from app.services.cache import TranslationCache
from app.services.rate_limiter import RateLimiter

# ── Logging ──────────────────────────────────────────────────
logger = logging.getLogger("signai")


# ── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("━" * 60)
    logger.info(f"🟢 {settings.APP_NAME} v{settings.APP_VERSION} starting")
    logger.info(f"   Environment : {settings.ENV}")
    logger.info(f"   Grammar AI  : {'OpenAI (' + settings.OPENAI_MODEL + ')' if settings.OPENAI_API_KEY else 'Rule-based (fallback)'}")
    logger.info(f"   Frontend URL: {settings.FRONTEND_URL}")
    logger.info("━" * 60)
    yield
    logger.info(f"🔴 {settings.APP_NAME} shutting down | Uptime: {analytics.uptime_formatted}")
    logger.info("━" * 60)


# ── App ──────────────────────────────────────────────────────

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="AI-powered sign language ↔ speech communication backend",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Middleware ───────────────────────────────────────────────

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ─────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch any unhandled exception and return a structured JSON error."""
    import traceback
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{req_id}] Unhandled exception on {request.method} {request.url.path}: {exc}")
    logger.debug(traceback.format_exc())
    analytics.record_error("http")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "request_id": req_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Structured JSON responses for HTTP exceptions (400, 404, 422, etc.)."""
    req_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail if isinstance(exc.detail, str) else "http_error",
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "request_id": req_id,
        },
    )


# ── Services ─────────────────────────────────────────────────

manager = ConnectionManager()
session_mgr = SessionManager()
grammar_engine = GrammarEngine()
translation_engine = TranslationEngine()
analytics = AnalyticsService()
cache = TranslationCache(max_size=256, ttl_seconds=3600)
ws_limiter = RateLimiter(
    rate=settings.WS_MAX_MESSAGES_PER_SECOND,
    capacity=settings.WS_MAX_MESSAGES_PER_SECOND * 2,
)

HEARTBEAT_INTERVAL = 30  # seconds


# ══════════════════════════════════════════════════════════════
# REST ENDPOINTS
# ══════════════════════════════════════════════════════════════


# ── Health ───────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    uptime: str
    services: dict
    config: dict

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check — returns server status, uptime, and service states."""
    return HealthResponse(
        status="online",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime=analytics.uptime_formatted,
        services={
            "grammar_engine": grammar_engine.get_status(),
            "translation_engine": translation_engine.get_status(),
            "active_connections": manager.active_count(),
            "active_sessions": session_mgr.active_count,
            "cache": cache.get_stats(),
        },
        config=settings.summary(),
    )


# ── Translate ────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Text to translate")
    mode: str = Field(..., pattern="^(SIGN_TO_SPEECH|SPEECH_TO_SIGN)$", description="Translation direction")
    language: Optional[str] = Field("en", description="Target language code")

class TranslateResponse(BaseModel):
    translated_text: str
    original_text: str
    mode: str
    confidence: float
    processing_time_ms: float

@app.post("/api/translate", response_model=TranslateResponse, tags=["Translation"])
async def translate_text(request: TranslateRequest):
    """One-off text translation (non-realtime). For real-time, use the WebSocket endpoint."""
    start = time.perf_counter()

    try:
        if request.mode == "SIGN_TO_SPEECH":
            # Check cache first
            cached = cache.get_grammar(request.text)
            if cached:
                corrected = cached
            else:
                corrected = await grammar_engine.process(request.text)
                cache.set_grammar(request.text, corrected)

            duration_ms = (time.perf_counter() - start) * 1000
            analytics.record_latency("grammar", duration_ms)
            analytics._total_translations += 1

            return TranslateResponse(
                translated_text=corrected,
                original_text=request.text,
                mode=request.mode,
                confidence=0.92,
                processing_time_ms=round(duration_ms, 1),
            )
        else:
            # Check cache first
            cached_signs = cache.get_sign(request.text)
            if cached_signs:
                sign_sequence = cached_signs
            else:
                sign_sequence = await translation_engine.speech_to_sign(request.text)
                cache.set_sign(request.text, sign_sequence)

            duration_ms = (time.perf_counter() - start) * 1000
            analytics.record_latency("translation", duration_ms)
            analytics._total_sign_conversions += 1

            return TranslateResponse(
                translated_text=" → ".join(sign_sequence),
                original_text=request.text,
                mode=request.mode,
                confidence=0.89,
                processing_time_ms=round(duration_ms, 1),
            )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        analytics._total_errors += 1
        raise HTTPException(status_code=500, detail=str(e))


# ── Analytics ────────────────────────────────────────────────

@app.get("/api/analytics", tags=["Analytics"])
async def get_analytics():
    """Retrieve system-wide analytics: translations, latency, sessions, uptime."""
    return {
        **analytics.get_summary(),
        "sessions": session_mgr.get_summary(),
        "cache": cache.get_stats(),
        "rate_limiter": ws_limiter.get_stats(),
    }


# ── Vocabulary ───────────────────────────────────────────────

@app.get("/api/vocabulary", tags=["Translation"])
async def get_vocabulary():
    """
    Returns the complete sign language vocabulary (English word → sign gesture mapping).
    Useful for the frontend to display available gestures and build UI components.
    """
    from app.services.translation_engine import SIGN_VOCABULARY, SKIP_WORDS

    return {
        "vocabulary": SIGN_VOCABULARY,
        "skip_words": list(SKIP_WORDS),
        "total_signs": len(set(SIGN_VOCABULARY.values())),
        "total_words": len(SIGN_VOCABULARY),
    }


# ── Grammar Rules ────────────────────────────────────────────

@app.get("/api/grammar-rules", tags=["Translation"])
async def get_grammar_rules():
    """
    Returns the rule-based grammar mappings used by the offline fallback engine.
    """
    from app.services.grammar_engine import GRAMMAR_RULES

    return {
        "rules": GRAMMAR_RULES,
        "total_rules": len(GRAMMAR_RULES),
        "engine_status": grammar_engine.get_status(),
    }


# ── Sessions ─────────────────────────────────────────────────

@app.get("/api/sessions", tags=["System"])
async def get_sessions():
    """List all active WebSocket sessions with their stats."""
    return session_mgr.get_summary()


# ── Cache ────────────────────────────────────────────────────

@app.get("/api/cache", tags=["System"])
async def get_cache_stats():
    """Translation cache statistics: entries, hit rate, size."""
    return cache.get_stats()

@app.delete("/api/cache", tags=["System"])
async def clear_cache():
    """Clear the translation cache."""
    cache.clear()
    return {"status": "cleared"}


# ══════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT (Real-time Pipeline)
# ══════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main real-time pipeline endpoint.

    Incoming message types:
      - gesture_sequence: Array of detected gestures → grammar AI → speech text
      - speech_input: Spoken text → sign language sequence
      - manual_text: Manual text input → process based on mode
      - set_mode: Switch translation mode for this session
      - ping: Keepalive ping

    Outgoing message types:
      - translation_result: Final translated text
      - sign_animation: Sign language animation sequence
      - grammar_processed: Grammar correction details
      - session_info: Session ID and metadata
      - pong: Keepalive response
      - error: Error details
    """
    await manager.connect(websocket)
    session = session_mgr.create_session(websocket)
    analytics.register_session(session.session_id)

    logger.info(f"Client connected [session={session.session_id}] | Active: {manager.active_count()}")

    # Send session info to the client
    await send_ws(websocket, "session_info", {
        "session_id": session.session_id,
        "mode": session.mode,
        "server_version": settings.APP_VERSION,
    })

    # Start server-side heartbeat task
    heartbeat_task = asyncio.create_task(
        _heartbeat_loop(websocket, session.session_id)
    )

    try:
        while True:
            raw = await websocket.receive_text()

            # Rate limiting check
            if not ws_limiter.check(session.session_id):
                await send_ws(websocket, "error", {
                    "message": "Rate limit exceeded. Slow down.",
                    "code": "RATE_LIMITED",
                })
                continue

            try:
                message = json.loads(raw)
                msg_type = message.get("type")
                payload = message.get("payload", {})

                logger.info(f"[WS:{session.session_id}] ← {msg_type}")

                if msg_type == "gesture_sequence":
                    session_mgr.record_gesture(websocket)
                    analytics.record_request(session.session_id, "gesture_sequence")
                    await handle_gesture_sequence(websocket, payload, session.session_id)

                elif msg_type == "speech_input":
                    session_mgr.record_speech(websocket)
                    analytics.record_request(session.session_id, "speech_input")
                    await handle_speech_input(websocket, payload, session.session_id)

                elif msg_type == "manual_text":
                    session_mgr.record_manual(websocket)
                    analytics.record_request(session.session_id, "manual_text")
                    await handle_manual_text(websocket, payload, session.session_id)

                elif msg_type == "set_mode":
                    new_mode = payload.get("mode", "SIGN_TO_SPEECH")
                    session_mgr.set_mode(websocket, new_mode)
                    await send_ws(websocket, "mode_changed", {"mode": new_mode})
                    logger.info(f"[WS:{session.session_id}] Mode → {new_mode}")

                elif msg_type == "ping":
                    await send_ws(websocket, "pong", {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "session_id": session.session_id,
                    })

                else:
                    await send_ws(websocket, "error", {"message": f"Unknown type: {msg_type}"})

            except json.JSONDecodeError:
                await send_ws(websocket, "error", {"message": "Invalid JSON"})
                session_mgr.record_error(websocket)
                analytics.record_error(session.session_id)

    except WebSocketDisconnect:
        pass
    finally:
        heartbeat_task.cancel()
        session_mgr.remove_session(websocket)
        analytics.unregister_session(session.session_id)
        manager.disconnect(websocket)
        logger.info(f"Client disconnected [session={session.session_id}] | Active: {manager.active_count()}")


# ══════════════════════════════════════════════════════════════
# PIPELINE HANDLERS
# ══════════════════════════════════════════════════════════════

async def handle_gesture_sequence(ws: WebSocket, payload: dict, session_id: str):
    """
    SIGN → SPEECH Pipeline:
    Gesture labels → Grammar Engine (LLM) → Natural text → Send for TTS
    """
    gestures = payload.get("gestures", [])
    if not gestures:
        await send_ws(ws, "error", {"message": "No gestures provided"})
        return

    start = time.perf_counter()

    # Step 1: Join raw gestures
    raw_text = " ".join(g.replace("_", " ").lower() for g in gestures)
    logger.info(f"[Pipeline:{session_id}] Raw gesture text: {raw_text}")

    # Step 2: Check cache first, then grammar engine
    cached = cache.get_grammar(raw_text)
    if cached:
        corrected_text = cached
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[Pipeline:{session_id}] Cache HIT: {corrected_text} ({duration_ms:.1f}ms)")
    else:
        corrected_text = await grammar_engine.process(raw_text)
        cache.set_grammar(raw_text, corrected_text)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[Pipeline:{session_id}] Corrected text: {corrected_text} ({duration_ms:.1f}ms)")

    analytics.record_latency("grammar", duration_ms)

    # Send grammar processing result
    await send_ws(ws, "grammar_processed", {
        "original": raw_text,
        "corrected": corrected_text,
        "latency_ms": round(duration_ms, 1),
        "cached": cached is not None,
    })

    # Step 3: Send final translation
    await send_ws(ws, "translation_result", {
        "translated_text": corrected_text,
        "source_gesture": " → ".join(gestures),
        "processing_time_ms": round(duration_ms, 1),
    })


async def handle_speech_input(ws: WebSocket, payload: dict, session_id: str):
    """
    SPEECH → SIGN Pipeline:
    Spoken text → Translation Engine → Sign language sequence
    """
    text = payload.get("text", "")
    if not text:
        await send_ws(ws, "error", {"message": "No text provided"})
        return

    start = time.perf_counter()
    logger.info(f"[Pipeline:{session_id}] Speech input: {text}")

    # Check cache first, then translation engine
    cached = cache.get_sign(text)
    if cached:
        sign_sequence = cached
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[Pipeline:{session_id}] Cache HIT: {sign_sequence} ({duration_ms:.1f}ms)")
    else:
        sign_sequence = await translation_engine.speech_to_sign(text)
        cache.set_sign(text, sign_sequence)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[Pipeline:{session_id}] Sign sequence: {sign_sequence} ({duration_ms:.1f}ms)")

    analytics.record_latency("translation", duration_ms)

    await send_ws(ws, "sign_animation", {
        "sign_sequence": sign_sequence,
        "source_text": text,
        "processing_time_ms": round(duration_ms, 1),
    })


async def handle_manual_text(ws: WebSocket, payload: dict, session_id: str):
    """Handle manual text input — route based on mode."""
    text = payload.get("text", "")
    mode = payload.get("mode", "SIGN_TO_SPEECH")

    start = time.perf_counter()

    if mode == "SIGN_TO_SPEECH":
        corrected = await grammar_engine.process(text)
        duration_ms = (time.perf_counter() - start) * 1000
        analytics.record_latency("grammar", duration_ms)
        await send_ws(ws, "translation_result", {
            "translated_text": corrected,
            "source_gesture": "MANUAL",
            "processing_time_ms": round(duration_ms, 1),
        })
    else:
        sign_sequence = await translation_engine.speech_to_sign(text)
        duration_ms = (time.perf_counter() - start) * 1000
        analytics.record_latency("translation", duration_ms)
        await send_ws(ws, "sign_animation", {
            "sign_sequence": sign_sequence,
            "source_text": text,
            "processing_time_ms": round(duration_ms, 1),
        })


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

async def send_ws(ws: WebSocket, msg_type: str, payload: dict):
    """Send a structured WebSocket message."""
    await ws.send_json({
        "type": msg_type,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).timestamp(),
    })


async def _heartbeat_loop(ws: WebSocket, session_id: str):
    """
    Server-side heartbeat: sends a ping every HEARTBEAT_INTERVAL seconds.
    If the client is dead, the send will raise an exception and the
    WebSocket handler's finally block will clean up.
    """
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await send_ws(ws, "heartbeat", {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
            })
    except Exception:
        pass  # Connection closed — cleanup happens in the main handler
