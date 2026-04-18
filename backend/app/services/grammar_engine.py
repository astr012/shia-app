# ============================================================
# SignAI_OS — Grammar Engine
# 
# Takes raw sign language gesture labels and restructures them
# into natural, grammatically correct spoken language.
#
# Sign language has its own grammar (e.g., ASL: "YOU HUNGRY?")
# which differs from spoken English ("Are you hungry?").
# This engine bridges that gap using an LLM.
#
# Supports:
#   - OpenAI GPT-4o / GPT-3.5 (primary)
#   - Rule-based fallback (offline)
# ============================================================

import os
import logging
from typing import Optional

logger = logging.getLogger("signai.grammar")

# Sign language grammar transformation rules (fallback)
GRAMMAR_RULES = {
    # Common ASL → English mappings
    "hello": "Hello!",
    "how are you": "How are you?",
    "how you": "How are you?",
    "thank you": "Thank you!",
    "thank": "Thank you!",
    "yes": "Yes.",
    "no": "No.",
    "help": "I need help.",
    "help me": "Can you help me?",
    "my name": "My name is",
    "what name you": "What is your name?",
    "where bathroom": "Where is the bathroom?",
    "please": "Please.",
    "sorry": "I'm sorry.",
    "understand": "I understand.",
    "not understand": "I don't understand.",
    "goodbye": "Goodbye!",
    "good morning": "Good morning!",
    "good night": "Good night!",
    "hungry": "I'm hungry.",
    "thirsty": "I'm thirsty.",
    "tired": "I'm tired.",
    "happy": "I'm happy!",
    "sad": "I'm sad.",
    "love you": "I love you.",
    "open palm": "Hello!",
    "point": "Look at that.",
    "fist": "Stop.",
    "peace": "Peace!",
    "three": "Three.",
    "four": "Four.",
}


class GrammarEngine:
    """
    Processes raw gesture text into natural spoken language.
    Uses OpenAI API when available, falls back to rule-based system.
    """

    def __init__(self):
        import time
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = None
        
        # Self-Healing Circuit Breaker Configuration
        self._llm_failures = 0
        self._llm_blacklist_until = 0
        self._failure_threshold = 3
        self._blacklist_duration_sec = 60

        if self.api_key:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
                logger.info(f"Grammar Engine initialized with OpenAI ({self.model})")
            except ImportError:
                logger.warning("openai package not installed. Using rule-based fallback.")
        else:
            logger.info("No OPENAI_API_KEY found. Using rule-based grammar engine.")

    async def process(self, raw_text: str) -> str:
        """
        Convert raw gesture labels into natural language.
        
        Args:
            raw_text: Space-separated gesture labels (e.g., "hello how you")
        
        Returns:
            Natural language text (e.g., "Hello! How are you?")
        """
        if not raw_text.strip():
            return ""

        import time
        
        # Self-Healing Check: Is the LLM route currently blacklisted?
        if self._llm_blacklist_until > time.time():
            logger.debug(f"LLM route blacklisted. Fast-failing to deterministic rules.")
            return self._process_with_rules(raw_text)

        # Try LLM first
        if self.client:
            try:
                result = await self._process_with_llm(raw_text)
                self._llm_failures = 0 # Reset on success
                return result
            except Exception as e:
                self._llm_failures += 1
                logger.error(f"LLM inference timeout/error ({self._llm_failures}/{self._failure_threshold}): {e}")
                
                # Trip the circuit breaker if threshold reached
                if self._llm_failures >= self._failure_threshold:
                    self._llm_blacklist_until = time.time() + self._blacklist_duration_sec
                    logger.critical(f"Circuit Breaker tripped! Blacklisting stochastic route for {self._blacklist_duration_sec}s.")
                    
                return self._process_with_rules(raw_text)

        # Standard Fallback to rule-based
        return self._process_with_rules(raw_text)

    async def _process_with_llm(self, raw_text: str) -> str:
        """Use OpenAI to restructure sign language grammar into spoken English."""
        system_prompt = """You are a sign language to spoken English translator. 
You receive raw gesture labels detected from sign language and must convert them 
into natural, grammatically correct English sentences.

Rules:
- Sign language uses different grammar than spoken English
- "YOU HUNGRY?" should become "Are you hungry?"
- "ME GO STORE" should become "I'm going to the store."
- Keep the meaning intact
- Make it sound natural and conversational
- Only output the translated text, nothing else
- If the input is a single greeting gesture, respond with the appropriate greeting"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Translate these sign language gestures to natural English: {raw_text}"},
            ],
            max_tokens=150,
            temperature=0.3,
        )

        result = response.choices[0].message.content.strip()
        logger.info(f"LLM translation: '{raw_text}' → '{result}'")
        return result

    def _process_with_rules(self, raw_text: str) -> str:
        """Rule-based grammar correction (offline fallback)."""
        normalized = raw_text.lower().strip()

        # Check exact match first
        if normalized in GRAMMAR_RULES:
            return GRAMMAR_RULES[normalized]

        # Check partial matches
        for pattern, replacement in GRAMMAR_RULES.items():
            if pattern in normalized:
                return replacement

        # Basic capitalization and punctuation
        result = normalized.capitalize()
        if not result.endswith(('.', '!', '?')):
            # If it looks like a question
            if any(q in normalized for q in ['what', 'where', 'when', 'why', 'how', 'who']):
                result += '?'
            else:
                result += '.'
        
        return result

    def get_status(self) -> str:
        """Return engine status."""
        if self.client:
            return f"openai:{self.model}"
        return "rule-based"
