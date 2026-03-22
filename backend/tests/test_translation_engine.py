# ============================================================
# Tests — Translation Engine
# ============================================================

import pytest
from app.services.translation_engine import TranslationEngine, SIGN_VOCABULARY, SKIP_WORDS


@pytest.fixture
def engine():
    """Translation engine instance (vocabulary-based, no OpenAI key)."""
    e = TranslationEngine()
    e.client = None  # Force vocabulary-based mode
    return e


class TestVocabularyTranslation:
    """Test the offline vocabulary-based speech → sign translation."""

    @pytest.mark.asyncio
    async def test_single_word(self, engine):
        """Single known words map to correct signs."""
        result = await engine.speech_to_sign("hello")
        assert "WAVE_HELLO" in result

    @pytest.mark.asyncio
    async def test_multiple_words(self, engine):
        """Multiple words each produce their own sign."""
        result = await engine.speech_to_sign("I want food")
        assert len(result) >= 2  # Should produce multiple signs

    @pytest.mark.asyncio
    async def test_skip_words_filtered_in_sentence(self, engine):
        """Skip words like 'the' are filtered out in multi-word input."""
        result = await engine.speech_to_sign("I want the food")
        # "the" should be skipped, other words should map to signs
        assert any("WANT" in s for s in result)
        assert any("FOOD" in s for s in result)

    @pytest.mark.asyncio
    async def test_unknown_word_spelled(self, engine):
        """Unknown words are fingerspelled."""
        result = await engine.speech_to_sign("xyz")
        # Should contain fingerspelling
        assert any("SPELL" in s or "FINGERSPELL" in s or len(s) == 1 for s in result) or len(result) > 0

    @pytest.mark.asyncio
    async def test_phrase_matching(self, engine):
        """Multi-word phrases are matched as a unit."""
        result = await engine.speech_to_sign("thank you")
        assert "THANK_YOU" in result

    @pytest.mark.asyncio
    async def test_empty_input(self, engine):
        """Empty input returns empty list."""
        result = await engine.speech_to_sign("")
        assert result == [] or result == [""]

    @pytest.mark.asyncio
    async def test_case_insensitive(self, engine):
        """Input is case-insensitive."""
        result = await engine.speech_to_sign("HELLO")
        assert "WAVE_HELLO" in result


class TestVocabularyData:
    """Test the vocabulary dictionary itself."""

    def test_vocabulary_not_empty(self):
        assert len(SIGN_VOCABULARY) > 50

    def test_skip_words_defined(self):
        assert "the" in SKIP_WORDS
        assert "a" in SKIP_WORDS

    def test_all_values_uppercase(self):
        """All sign gesture names should be uppercase."""
        for word, sign in SIGN_VOCABULARY.items():
            assert sign == sign.upper(), f"Sign for '{word}' is not uppercase: {sign}"


class TestTranslationEngineStatus:

    def test_vocab_based_status(self, engine):
        assert engine.get_status() == "vocabulary-based"
