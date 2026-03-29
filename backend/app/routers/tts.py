# ============================================================
# SignAI_OS — Text-to-Speech Router
#
# Endpoints: /api/tts, /api/tts/voices
# ============================================================

import base64
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.dependencies import tts_engine

router = APIRouter(prefix="/api/tts", tags=["TTS"])


# ── Models ───────────────────────────────────────────────────

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Text to synthesize")
    voice: Optional[str] = Field(None, description="Voice name or alias")


# ── Endpoints ────────────────────────────────────────────────

@router.post("")
async def synthesize_speech(request: TTSRequest):
    """
    Server-side TTS — generates natural audio using Microsoft Neural Voices.
    Returns base64-encoded MP3 audio that sounds identical on ALL devices.
    Falls back to text-only response if edge-tts is not installed.
    """
    audio_bytes = await tts_engine.synthesize(request.text, request.voice)

    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return {
            "audio": audio_b64,
            "format": "mp3",
            "engine": "edge-tts",
            "voice": request.voice or tts_engine.voice,
            "text": request.text,
        }
    else:
        return {
            "audio": None,
            "format": "browser-tts",
            "engine": "browser-fallback",
            "text": request.text,
        }


@router.get("/voices")
async def list_tts_voices():
    """List all available neural voices for TTS."""
    voices = await tts_engine.list_voices()
    return {
        "voices": voices,
        "total": len(voices),
        "engine": tts_engine.get_status(),
    }
