# ============================================================
# SignAI_OS — Dependency Injection Registry
#
# Central singleton registry for all services. Routers import
# service instances from here to avoid circular dependencies
# and ensure single-instance semantics.
# ============================================================

from app.config import settings
from app.services.grammar_engine import GrammarEngine
from app.services.translation_engine import TranslationEngine
from app.services.connection_manager import ConnectionManager
from app.services.session_manager import SessionManager
from app.services.analytics import AnalyticsService
from app.services.cache import TranslationCache
from app.services.rate_limiter import RateLimiter
from app.services.tts_engine import TTSEngine
from app.services.ml_classifier import GestureClassifier

# ── Service Singletons ──────────────────────────────────────

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
tts_engine = TTSEngine()
classifier = GestureClassifier(confidence_threshold=0.7)

HEARTBEAT_INTERVAL = 30  # seconds
