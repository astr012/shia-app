# ============================================================
# SignAI_OS — Translation Engine
#
# Handles the SPEECH → SIGN direction:
# Takes natural spoken text and breaks it down into a sequence
# of sign language gestures/signs that can be animated.
#
# Also handles vocabulary management and custom gesture mapping.
# ============================================================

import os
import logging
from typing import List, Optional

logger = logging.getLogger("signai.translation")

# ── Sign Language Vocabulary ─────────────────────────────────
# Maps English words/phrases to sign language gesture names.
# In production, this would be a database-backed dictionary.

SIGN_VOCABULARY = {
    # Greetings
    "hello": "WAVE_HELLO",
    "hi": "WAVE_HELLO",
    "goodbye": "WAVE_BYE",
    "bye": "WAVE_BYE",
    "good morning": "GOOD + MORNING",
    "good night": "GOOD + NIGHT",
    "good afternoon": "GOOD + AFTERNOON",
    "welcome": "WELCOME",
    
    # Common phrases
    "thank you": "THANK_YOU",
    "thanks": "THANK_YOU",
    "please": "PLEASE",
    "sorry": "SORRY",
    "excuse me": "EXCUSE_ME",
    "you're welcome": "WELCOME",
    "how are you": "HOW + POINT_FORWARD",
    "nice to meet you": "NICE + MEET + POINT_FORWARD",
    
    # Pronouns
    "i": "POINT_SELF",
    "me": "POINT_SELF",
    "you": "POINT_FORWARD",
    "he": "POINT_RIGHT",
    "she": "POINT_RIGHT",
    "we": "SWEEP_SELF",
    "they": "SWEEP_FORWARD",
    "my": "PALM_CHEST",
    "mine": "PALM_CHEST",
    "your": "PALM_FORWARD",
    "yours": "PALM_FORWARD",
    
    # Questions
    "what": "WHAT",
    "where": "WHERE",
    "when": "WHEN",
    "why": "WHY",
    "how": "HOW",
    "who": "WHO",
    "which": "WHICH",
    
    # Verbs
    "am": "BE",
    "is": "BE",
    "are": "BE",
    "want": "WANT",
    "need": "NEED",
    "help": "HELP",
    "go": "GO",
    "come": "COME",
    "eat": "EAT",
    "drink": "DRINK",
    "sleep": "SLEEP",
    "work": "WORK",
    "know": "KNOW",
    "understand": "UNDERSTAND",
    "like": "LIKE",
    "love": "LOVE",
    "have": "HAVE",
    "can": "CAN",
    "will": "WILL",
    "think": "THINK",
    "feel": "FEEL",
    "hear": "HEAR",
    "see": "SEE",
    "look": "SEE",
    "say": "SAY",
    "tell": "SAY",
    "talk": "SAY",
    "ask": "ASK",
    "answer": "ANSWER",
    "learn": "LEARN",
    "teach": "TEACH",
    "practice": "PRACTICE",
    "try": "TRY",
    "give": "GIVE",
    "take": "TAKE",
    "make": "MAKE",
    "use": "USE",
    "play": "PLAY",
    "meet": "MEET",
    "sit": "SIT",
    "stand": "STAND",
    "walk": "WALK",
    "run": "RUN",
    "stop": "OPEN_PALM",
    "wait": "OPEN_PALM",
    "call": "CALL_ME",
    "call me": "CALL_ME",
    "open": "OPEN_PALM",
    "close": "FIST",
    "start": "START",
    "begin": "START",
    "finish": "FINISH",
    "done": "FINISH",
    
    # Adjectives / States
    "happy": "HAPPY",
    "sad": "SAD",
    "angry": "ANGRY",
    "scared": "SCARED",
    "sick": "SICK",
    "hurt": "HURT",
    "hungry": "HUNGRY",
    "thirsty": "THIRSTY",
    "tired": "TIRED",
    "good": "GOOD",
    "bad": "BAD",
    "big": "BIG",
    "small": "SMALL",
    "hot": "HOT",
    "cold": "COLD",
    "beautiful": "BEAUTIFUL",
    "ugly": "UGLY",
    "fast": "FAST",
    "slow": "SLOW",
    "hard": "HARD",
    "easy": "EASY",
    "right": "RIGHT",
    "wrong": "WRONG",
    
    # Nouns
    "name": "NAME",
    "family": "FAMILY",
    "friend": "FRIEND",
    "home": "HOME",
    "house": "HOME",
    "school": "SCHOOL",
    "workplace": "WORK",
    "water": "WATER",
    "food": "FOOD",
    "bathroom": "BATHROOM",
    "toilet": "BATHROOM",
    "phone": "PHONE",
    "book": "BOOK",
    "car": "CAR",
    "computer": "COMPUTER",
    "doctor": "DOCTOR",
    "hospital": "HOSPITAL",
    "time": "TIME",
    "day": "DAY",
    "night": "NIGHT",
    "morning": "MORNING",
    "afternoon": "AFTERNOON",
    "week": "WEEK",
    "month": "MONTH",
    "year": "YEAR",
    "today": "TODAY",
    "tomorrow": "TOMORROW",
    "yesterday": "YESTERDAY",
    "now": "NOW",
    
    # Numbers
    "zero": "ZERO",
    "one": "ONE",
    "two": "TWO",
    "three": "THREE",
    "four": "FOUR",
    "five": "FIVE",
    "six": "SIX",
    "seven": "SEVEN",
    "eight": "EIGHT",
    "nine": "NINE",
    "ten": "TEN",
    
    # Responses / Concepts
    "yes": "YES_NOD",
    "no": "NO_SHAKE",
    "maybe": "MAYBE",
    "okay": "OK_SIGN",
    "peace": "PEACE",
    "fist": "FIST",
    "rock": "HORNS",
    "money": "PINCH",
    "more": "MORE",
    "less": "LESS",
    "again": "AGAIN",
    "same": "SAME",
    "different": "DIFFERENT",
}

# Words to skip (articles, prepositions that sign language typically omits)
SKIP_WORDS = {
    "the", "a", "an", "to", "of", "in", "on", "at", "for", "with",
    "it", "its", "this", "that", "do", "does", "did", "been", "being",
    "would", "could", "should", "very", "really", "just",
}


class TranslationEngine:
    """
    Converts spoken English text into sign language gesture sequences.
    """

    def __init__(self):
        import time
        self.api_key = os.getenv("OPENAI_API_KEY")
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
                logger.info("Translation Engine initialized with OpenAI")
            except ImportError:
                logger.warning("openai package not installed. Using vocabulary-based translation.")
        else:
            logger.info("Translation Engine using vocabulary-based translation.")

    async def speech_to_sign(self, text: str) -> List[str]:
        """
        Convert spoken English text into a sequence of sign gesture names.
        
        Args:
            text: Natural English text (e.g., "Hello, how are you?")
        
        Returns:
            List of sign gesture names (e.g., ["WAVE_HELLO", "HOW", "BE", "POINT_FORWARD"])
        """
        if not text.strip():
            return []

        import time

        # Self-Healing Check: Is the LLM route currently blacklisted?
        if self._llm_blacklist_until > time.time():
            logger.debug(f"LLM route blacklisted. Fast-failing to deterministic vocabulary rules.")
            return self._translate_with_vocabulary(text)

        # Try LLM for better phrase decomposition
        if self.client:
            try:
                result = await self._translate_with_llm(text)
                self._llm_failures = 0
                return result
            except Exception as e:
                self._llm_failures += 1
                logger.error(f"LLM translation failed ({self._llm_failures}/{self._failure_threshold}): {e}")
                
                # Trip the circuit breaker if threshold reached
                if self._llm_failures >= self._failure_threshold:
                    self._llm_blacklist_until = time.time() + self._blacklist_duration_sec
                    logger.critical(f"Circuit Breaker tripped! Blacklisting stochastic route for {self._blacklist_duration_sec}s.")
                    
                return self._translate_with_vocabulary(text)

        # Vocabulary-based fallback
        return self._translate_with_vocabulary(text)

    async def _translate_with_llm(self, text: str) -> List[str]:
        """Use OpenAI to decompose text into sign gestures."""
        available_signs = ", ".join(sorted(set(SIGN_VOCABULARY.values())))

        system_prompt = f"""You are a spoken English to sign language translator.
Convert the given English text into a sequence of sign language gestures.

Available signs: {available_signs}

Rules:
- Output ONLY a comma-separated list of sign names from the available list
- Sign language omits articles (the, a, an) and some prepositions
- Use the closest available sign for each concept
- Keep the sequence in a logical order for sign language grammar
- Sign language grammar is different: questions go at the end, time references at the beginning
- Example: "Are you hungry?" → "POINT_FORWARD, HUNGRY, WHAT"
"""

        response = await self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Translate to sign language: {text}"},
            ],
            max_tokens=100,
            temperature=0.2,
        )

        result = response.choices[0].message.content.strip()
        signs = [s.strip() for s in result.split(",") if s.strip()]
        logger.info(f"LLM sign translation: '{text}' → {signs}")
        return signs

    def _translate_with_vocabulary(self, text: str) -> List[str]:
        """Vocabulary-based translation (offline fallback)."""
        # Clean and tokenize
        cleaned = text.lower().strip()
        for char in '.,!?;:\'"()[]{}':
            cleaned = cleaned.replace(char, '')

        words = cleaned.split()
        signs = []

        i = 0
        while i < len(words):
            # Try multi-word phrases first (longest match)
            matched = False
            for length in range(min(3, len(words) - i), 0, -1):
                phrase = " ".join(words[i:i + length])
                if phrase in SIGN_VOCABULARY:
                    signs.append(SIGN_VOCABULARY[phrase])
                    i += length
                    matched = True
                    break

            if not matched:
                word = words[i]
                if word not in SKIP_WORDS:
                    if word in SIGN_VOCABULARY:
                        signs.append(SIGN_VOCABULARY[word])
                    else:
                        # Fingerspell unknown words
                        signs.append(f"SPELL:{word.upper()}")
                i += 1

        logger.info(f"Vocabulary translation: '{text}' → {signs}")
        return signs if signs else ["UNKNOWN_GESTURE"]

    def get_status(self) -> str:
        """Return engine status."""
        if self.client:
            return "openai-enhanced"
        return "vocabulary-based"
