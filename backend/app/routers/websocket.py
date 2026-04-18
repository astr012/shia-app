# ============================================================
# SignAI_OS — WebSocket Router
#
# Real-time pipeline endpoint: /ws
# Handles gesture sequences, speech input, manual text,
# WebRTC signaling, mode switching, and heartbeats.
# ============================================================

import time
import json
import base64
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketClose

from app.config import settings
from app.dependencies import (
    manager, session_mgr, grammar_engine, translation_engine,
    analytics, cache, ws_limiter, tts_engine, HEARTBEAT_INTERVAL,
    classifier
)

logger = logging.getLogger("signai")

router = APIRouter()


# ══════════════════════════════════════════════════════════════
# WEBSOCKET ENDPOINT
# ══════════════════════════════════════════════════════════════

def _verify_ws_token(token: str | None) -> str | None:
    """Verify JWT from WS query param. Returns username or None."""
    if not token:
        return None
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except Exception:
        return "__invalid__"


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = Query(default=None)):
    """
    Main real-time pipeline endpoint.
    Optional auth: pass ?token=<JWT> to authenticate the session.
    """
    # Verify token if provided
    ws_user = _verify_ws_token(token)
    if ws_user == "__invalid__":
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    await manager.connect(websocket)
    session = session_mgr.create_session(websocket)
    analytics.register_session(session.session_id)

    logger.info(f"Client connected [session={session.session_id}] [user={ws_user or 'anon'}] | Active: {manager.active_count()}")

    # Send session info to the client
    await _send_ws(websocket, "session_info", {
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
                await _send_ws(websocket, "error", {
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
                    await _handle_gesture_sequence(websocket, payload, session.session_id)

                elif msg_type == "speech_input":
                    session_mgr.record_speech(websocket)
                    analytics.record_request(session.session_id, "speech_input")
                    await _handle_speech_input(websocket, payload, session.session_id)

                elif msg_type == "manual_text":
                    session_mgr.record_manual(websocket)
                    analytics.record_request(session.session_id, "manual_text")
                    await _handle_manual_text(websocket, payload, session.session_id)

                elif msg_type == "set_mode":
                    new_mode = payload.get("mode", "SIGN_TO_SPEECH")
                    session_mgr.set_mode(websocket, new_mode)
                    await _send_ws(websocket, "mode_changed", {"mode": new_mode})
                    logger.info(f"[WS:{session.session_id}] Mode → {new_mode}")

                elif msg_type == "ping":
                    await _send_ws(websocket, "pong", {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "session_id": session.session_id,
                    })

                elif msg_type in ["webrtc_offer", "webrtc_answer", "webrtc_ice"]:
                    target_session_id = payload.get("target_session_id")
                    if target_session_id:
                        target_session = session_mgr.get_session_by_id(target_session_id)
                        if target_session:
                            logger.info(f"[WS:{session.session_id}] Routed WebRTC {msg_type} to {target_session_id}")
                            await manager.send_to(target_session.websocket, {
                                "type": msg_type,
                                "payload": {
                                    "from_session": session.session_id,
                                    "data": payload.get("data")
                                }
                            })
                        else:
                            await _send_ws(websocket, "error", {"message": "Target session not found"})

                else:
                    await _send_ws(websocket, "error", {"message": f"Unknown type: {msg_type}"})

            except json.JSONDecodeError:
                await _send_ws(websocket, "error", {"message": "Invalid JSON"})
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

async def _handle_gesture_sequence(ws: WebSocket, payload: dict, session_id: str):
    """
    SIGN → SPEECH Pipeline:
    Landmark seq / Gesture labels → ML Classify → Grammar Engine (LLM) → Natural text → Send for TTS
    """
    # Try getting pre-classified labels first
    gestures = payload.get("gestures", [])
    
    # Check for raw ML landmarks
    landmarks = payload.get("landmarks", [])
    ml_confidence_metrics = []

    if landmarks:
        # Pass the entire buffer window for temporal classification
        best_label, temp_conf = classifier.classify_temporal(landmarks)
        if best_label:
            gestures = [best_label]
            ml_confidence_metrics.append({
                "temporal_window_size": len(landmarks), 
                "label": best_label, 
                "confidence": round(temp_conf, 3)
            })

    if not gestures:
        await _send_ws(ws, "error", {"message": "No valid gestures or landmarks provided"})
        return

    start = time.perf_counter()

    # Step 1: Join raw gestures (fallback tertiary layer)
    raw_text = " ".join(g.replace("_", " ").lower() for g in gestures)
    logger.info(f"[Pipeline:{session_id}] Raw gesture text: {raw_text}")

    # Step 2: Check cache first, then grammar engine (primary/secondary layer)
    cached = await cache.get_grammar(raw_text)
    if cached:
        corrected_text = cached
        duration_ms = float((time.perf_counter() - start) * 1000)
        logger.info(f"[Pipeline:{session_id}] Cache HIT: {corrected_text} ({duration_ms:.1f}ms)")
    else:
        corrected_text = await grammar_engine.process(raw_text)
        await cache.set_grammar(raw_text, corrected_text)
        duration_ms = float((time.perf_counter() - start) * 1000)
        logger.info(f"[Pipeline:{session_id}] Corrected text: {corrected_text} ({duration_ms:.1f}ms)")

    analytics.record_latency("grammar", duration_ms)

    # Send grammar processing result
    await _send_ws(ws, "grammar_processed", {
        "original": raw_text,
        "corrected": corrected_text,
        "latency_ms": round(duration_ms, 1),
        "cached": cached is not None,
    })

    # Step 3: Generate TTS audio server-side
    audio_b64 = None
    if tts_engine.is_available:
        audio_bytes = await tts_engine.synthesize(corrected_text)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    # Step 4: Send final translation + audio
    await _send_ws(ws, "translation_result", {
        "translated_text": corrected_text,
        "source_gesture": " → ".join(gestures),
        "processing_time_ms": round(duration_ms, 1),
        "audio": audio_b64,
        "audio_format": "mp3" if audio_b64 else None,
        "ml_metrics": ml_confidence_metrics,
    })


async def _handle_speech_input(ws: WebSocket, payload: dict, session_id: str):
    """
    SPEECH → SIGN Pipeline:
    Spoken text → Translation Engine → Sign language sequence
    """
    text = payload.get("text", "")
    if not text:
        await _send_ws(ws, "error", {"message": "No text provided"})
        return

    start = time.perf_counter()
    logger.info(f"[Pipeline:{session_id}] Speech input: {text}")

    cached = await cache.get_sign(text)
    if cached:
        sign_sequence = cached
        duration_ms = float((time.perf_counter() - start) * 1000)
        logger.info(f"[Pipeline:{session_id}] Cache HIT: {sign_sequence} ({duration_ms:.1f}ms)")
    else:
        sign_sequence = await translation_engine.speech_to_sign(text)
        await cache.set_sign(text, sign_sequence)
        duration_ms = float((time.perf_counter() - start) * 1000)
        logger.info(f"[Pipeline:{session_id}] Sign sequence: {sign_sequence} ({duration_ms:.1f}ms)")

    analytics.record_latency("translation", duration_ms)

    await _send_ws(ws, "sign_animation", {
        "sign_sequence": sign_sequence,
        "source_text": text,
        "processing_time_ms": round(duration_ms, 1),
    })


async def _handle_manual_text(ws: WebSocket, payload: dict, session_id: str):
    """Handle manual text input — route based on mode. Uses cache to avoid redundant LLM calls."""
    text = payload.get("text", "")
    mode = payload.get("mode", "SIGN_TO_SPEECH")

    start = time.perf_counter()

    if mode == "SIGN_TO_SPEECH":
        # Check cache first
        cached = await cache.get_grammar(text)
        if cached:
            corrected = cached
        else:
            corrected = await grammar_engine.process(text)
            await cache.set_grammar(text, corrected)

        duration_ms = float((time.perf_counter() - start) * 1000)
        analytics.record_latency("grammar", duration_ms)
        await _send_ws(ws, "translation_result", {
            "translated_text": corrected,
            "source_gesture": "MANUAL",
            "processing_time_ms": round(duration_ms, 1),
        })
    else:
        # Check cache first
        cached_signs = await cache.get_sign(text)
        if cached_signs:
            sign_sequence = cached_signs
        else:
            sign_sequence = await translation_engine.speech_to_sign(text)
            await cache.set_sign(text, sign_sequence)

        duration_ms = float((time.perf_counter() - start) * 1000)
        analytics.record_latency("translation", duration_ms)
        await _send_ws(ws, "sign_animation", {
            "sign_sequence": sign_sequence,
            "source_text": text,
            "processing_time_ms": round(duration_ms, 1),
        })


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

async def _send_ws(ws: WebSocket, msg_type: str, payload: dict):
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
            await _send_ws(ws, "heartbeat", {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
            })
    except Exception:
        pass  # Connection closed — cleanup happens in the main handler
