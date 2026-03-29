# ============================================================
# SignAI_OS — Translation Router
#
# Endpoints: /api/translate, /api/vocabulary, /api/grammar-rules
# ============================================================

import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import grammar_engine, translation_engine, analytics, cache

logger = logging.getLogger("signai")

router = APIRouter(prefix="/api", tags=["Translation"])


# ── Models ───────────────────────────────────────────────────

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


# ── Endpoints ────────────────────────────────────────────────

@router.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """One-off text translation (non-realtime). For real-time, use the WebSocket endpoint."""
    start = time.perf_counter()

    try:
        if request.mode == "SIGN_TO_SPEECH":
            cached = cache.get_grammar(request.text)
            if cached:
                corrected = cached
            else:
                corrected = await grammar_engine.process(request.text)
                cache.set_grammar(request.text, corrected)

            duration_ms = float((time.perf_counter() - start) * 1000)
            analytics.record_latency("grammar", duration_ms)

            return TranslateResponse(
                translated_text=corrected,
                original_text=request.text,
                mode=request.mode,
                confidence=0.92,
                processing_time_ms=round(duration_ms, 1),
            )
        else:
            cached_signs = cache.get_sign(request.text)
            if cached_signs:
                sign_sequence = cached_signs
            else:
                sign_sequence = await translation_engine.speech_to_sign(request.text)
                cache.set_sign(request.text, sign_sequence)

            duration_ms = float((time.perf_counter() - start) * 1000)
            analytics.record_latency("translation", duration_ms)

            return TranslateResponse(
                translated_text=" → ".join(sign_sequence),
                original_text=request.text,
                mode=request.mode,
                confidence=0.89,
                processing_time_ms=round(duration_ms, 1),
            )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        analytics.record_error("http")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vocabulary")
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


@router.get("/grammar-rules")
async def get_grammar_rules():
    """Returns the rule-based grammar mappings used by the offline fallback engine."""
    from app.services.grammar_engine import GRAMMAR_RULES

    return {
        "rules": GRAMMAR_RULES,
        "total_rules": len(GRAMMAR_RULES),
        "engine_status": grammar_engine.get_status(),
    }
