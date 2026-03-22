# ============================================================
# Tests — Grammar Engine
# ============================================================

import pytest
from app.services.grammar_engine import GrammarEngine, GRAMMAR_RULES


@pytest.fixture
def engine():
    """Grammar engine instance (rule-based, no OpenAI key)."""
    e = GrammarEngine()
    e.client = None  # Force rule-based mode
    return e


class TestRuleBasedGrammar:
    """Test the offline rule-based grammar correction."""

    @pytest.mark.asyncio
    async def test_exact_match(self, engine):
        """Exact rule match returns the mapped value."""
        assert await engine.process("hello") == "Hello!"
        assert await engine.process("how you") == "How are you?"
        assert await engine.process("thank you") == "Thank you!"

    @pytest.mark.asyncio
    async def test_case_insensitive(self, engine):
        """Input is normalized to lowercase before matching."""
        assert await engine.process("HELLO") == "Hello!"
        assert await engine.process("How You") == "How are you?"

    @pytest.mark.asyncio
    async def test_whitespace_trimming(self, engine):
        """Leading/trailing whitespace is trimmed."""
        assert await engine.process("  hello  ") == "Hello!"

    @pytest.mark.asyncio
    async def test_partial_match(self, engine):
        """Partial matches are found within longer strings."""
        result = await engine.process("hello friend")
        assert result == "Hello!"  # "hello" is a partial match

    @pytest.mark.asyncio
    async def test_unknown_adds_period(self, engine):
        """Unknown text is capitalized and gets a period."""
        result = await engine.process("some random words")
        assert result == "Some random words."

    @pytest.mark.asyncio
    async def test_question_detection(self, engine):
        """Text containing question words gets matched or question-marked."""
        # "where" is a known rule key → returns "Where is the bathroom?"
        result = await engine.process("where")
        assert "Where" in result

    @pytest.mark.asyncio
    async def test_empty_input(self, engine):
        """Empty input returns empty string."""
        assert await engine.process("") == ""
        assert await engine.process("   ") == ""

    @pytest.mark.asyncio
    async def test_gesture_labels(self, engine):
        """Common gesture labels are correctly transformed."""
        assert await engine.process("open palm") == "Hello!"
        assert await engine.process("peace") == "Peace!"
        assert await engine.process("fist") == "Stop."


class TestGrammarEngineStatus:
    """Test engine status reporting."""

    def test_rule_based_status(self, engine):
        assert engine.get_status() == "rule-based"

    def test_all_rules_exist(self):
        """Verify all expected rules are present."""
        assert len(GRAMMAR_RULES) >= 25
        assert "hello" in GRAMMAR_RULES
        assert "goodbye" in GRAMMAR_RULES
