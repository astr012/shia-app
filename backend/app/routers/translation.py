# ============================================================
# SignAI_OS â€” Translation Router
#
# Endpoints: /api/translate, /api/vocabulary, /api/grammar-rules
# ============================================================

import re
import html
import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import grammar_engine, translation_engine, analytics, cache

logger = logging.getLogger("signai")

router = APIRouter(prefix="/api", tags=["Translation"])


# â”€â”€ Input Sanitization â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize_input(text: str) -> str:
    """
    Strip HTML/script tags and normalize whitespace.
    Prevents XSS vectors from propagating through the translation pipeline.
    """
    # Unescape any HTML entities, then strip tags
    cleaned = html.unescape(text)
    cleaned = _HTML_TAG_RE.sub("", cleaned)
    # Collapse whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


# â”€â”€ Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€ Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """One-off text translation (non-realtime). For real-time, use the WebSocket endpoint."""
    start = time.perf_counter()

    # Sanitize input to prevent XSS propagation
    sanitized_text = _sanitize_input(request.text)

    try:
        if request.mode == "SIGN_TO_SPEECH":
            cached = await cache.get_grammar(sanitized_text)
            if cached:
                corrected = cached
            else:
                corrected = await grammar_engine.process(sanitized_text)
                await cache.set_grammar(sanitized_text, corrected)

            duration_ms = float((time.perf_counter() - start) * 1000)
            analytics.record_latency("grammar", duration_ms)
            
            # Simple confidence rule for text grammar
            conf = 1.0 if grammar_engine.get_status().startswith("openai") else 0.85

            return TranslateResponse(
                translated_text=corrected,
                original_text=sanitized_text,
                mode=request.mode,
                confidence=conf,
                processing_time_ms=round(duration_ms, 1),
            )
        else:
            cached_signs = await cache.get_sign(sanitized_text)
            if cached_signs:
                sign_sequence = cached_signs
            else:
                sign_sequence = await translation_engine.speech_to_sign(sanitized_text)
                await cache.set_sign(sanitized_text, sign_sequence)

            duration_ms = float((time.perf_counter() - start) * 1000)
            analytics.record_latency("translation", duration_ms)

            # Dynamic confidence based on fingerspelling vs real signs coverage
            if not sign_sequence:
                conf = 0.0
            else:
                known_signs = sum(1 for s in sign_sequence if not s.startswith("SPELL:") and s != "UNKNOWN_GESTURE")
                conf = max(0.2, round(known_signs / len(sign_sequence), 2))

            return TranslateResponse(
                translated_text=" â†’ ".join(sign_sequence),
                original_text=request.text,
                mode=request.mode,
                confidence=conf,
                processing_time_ms=round(duration_ms, 1),
            )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        analytics.record_error("http")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vocabulary")
async def get_vocabulary():
    """
    Returns the complete sign language vocabulary (English word â†’ sign gesture mapping).
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
