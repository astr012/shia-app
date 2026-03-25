# ============================================================
# SignAI_OS — Text-to-Speech Engine
# Provides natural-sounding voice synthesis for ALL devices
#
# Strategy:
#   1. edge-tts (Microsoft Neural Voices) — FREE, human-like
#   2. Fallback: returns text for browser-side TTS
#
# The audio is generated server-side, so quality is identical
# on every device (phones, tablets, old laptops, etc.)
# ============================================================

import io
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("signai")

# Default voice — Microsoft's natural neural voices
# These sound significantly better than browser TTS on ANY device
DEFAULT_VOICE = "en-US-JennyNeural"     # Female, warm
ALTERNATIVE_VOICES = {
    "female_warm":  "en-US-JennyNeural",
    "female_clear": "en-US-AriaNeural",
    "male_warm":    "en-US-GuyNeural",
    "male_clear":   "en-US-ChristopherNeural",
    "female_uk":    "en-GB-SoniaNeural",
    "male_uk":      "en-GB-RyanNeural",
    "female_au":    "en-AU-NatashaNeural",
    "male_in":      "en-IN-PrabhatNeural",
    "female_in":    "en-IN-NeerjaNeural",
}

# Check if edge-tts is available
_edge_tts_available = False
try:
    import edge_tts
    _edge_tts_available = True
    logger.info("✅ edge-tts loaded — natural voice synthesis available")
except ImportError:
    logger.warning("⚠️  edge-tts not installed. Install with: pip install edge-tts")
    logger.warning("   Falling back to browser-side TTS (lower quality)")


class TTSEngine:
    """Server-side Text-to-Speech engine using Microsoft Neural Voices."""

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self._available = _edge_tts_available

    @property
    def is_available(self) -> bool:
        return self._available

    def get_status(self) -> dict:
        return {
            "engine": "edge-tts (Microsoft Neural)" if self._available else "browser-fallback",
            "voice": self.voice if self._available else "browser-default",
            "available_voices": len(ALTERNATIVE_VOICES) if self._available else 0,
        }

    async def synthesize(self, text: str, voice: Optional[str] = None) -> Optional[bytes]:
        """
        Convert text to speech audio (MP3 bytes).
        Returns None if edge-tts is not available (frontend should use browser TTS).
        Works identically on ALL devices since synthesis happens server-side.
        """
        if not self._available:
            return None

        if not text or not text.strip():
            return None

        selected_voice = voice or self.voice

        # Resolve voice aliases
        if selected_voice in ALTERNATIVE_VOICES:
            selected_voice = ALTERNATIVE_VOICES[selected_voice]

        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate=self.rate,
                pitch=self.pitch,
            )

            # Collect audio bytes
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_bytes = audio_buffer.getvalue()

            if len(audio_bytes) == 0:
                logger.warning(f"[TTS] Empty audio for text: {text[:50]}")
                return None

            logger.info(f"[TTS] Synthesized {len(audio_bytes)} bytes for: {text[:50]}...")
            return audio_bytes

        except Exception as e:
            logger.error(f"[TTS] Synthesis failed: {e}")
            return None

    async def list_voices(self) -> list:
        """List all available Microsoft Neural voices."""
        if not self._available:
            return []

        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            # Filter to English voices only
            english_voices = [
                {
                    "name": v["ShortName"],
                    "gender": v["Gender"],
                    "locale": v["Locale"],
                }
                for v in voices
                if v["Locale"].startswith("en-")
            ]
            return english_voices
        except Exception as e:
            logger.error(f"[TTS] Failed to list voices: {e}")
            return []
