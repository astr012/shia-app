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
    
    # Common phrases
    "thank you": "THANK_YOU",
    "thanks": "THANK_YOU",
    "please": "PLEASE",
    "sorry": "SORRY",
    "excuse me": "EXCUSE_ME",
    "you're welcome": "WELCOME",
    
    # Pronouns
    "i": "POINT_SELF",
    "me": "POINT_SELF",
    "you": "POINT_FORWARD",
    "he": "POINT_RIGHT",
    "she": "POINT_RIGHT",
    "we": "SWEEP_SELF",
    "they": "SWEEP_FORWARD",
    
    # Questions
    "what": "WHAT",
    "where": "WHERE",
    "when": "WHEN",
    "why": "WHY",
    "how": "HOW",
    "who": "WHO",
    
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
    
    # Adjectives / States
    "happy": "HAPPY",
    "sad": "SAD",
    "hungry": "HUNGRY",
    "thirsty": "THIRSTY",
    "tired": "TIRED",
    "good": "GOOD",
    "bad": "BAD",
    "big": "BIG",
    "small": "SMALL",
    
    # Nouns
    "name": "NAME",
    "family": "FAMILY",
    "friend": "FRIEND",
    "home": "HOME",
    "school": "SCHOOL",
    "water": "WATER",
    "food": "FOOD",
    "bathroom": "BATHROOM",
    "phone": "PHONE",
    "book": "BOOK",
    
    # Numbers
    "one": "ONE",
    "two": "TWO",
    "three": "THREE",
    "four": "FOUR",
    "five": "FIVE",
    
    # Responses
    "yes": "YES_NOD",
    "no": "NO_SHAKE",
    "maybe": "MAYBE",
    "okay": "OK_SIGN",
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
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None

        if self.api_key:
            try:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key)
                logger.info("Translation Engine initialized with OpenAI")
            except ImportError:
                logger.warning("openai package not installed. Using vocabulary-based translation.")
        else:
            logger.info("Translation Engine using vocabulary-based translation.")

    async def speech_to_sign(self, text: str, custom_dict: Optional[dict] = None) -> List[str]:
        """
        Convert spoken English text into a sequence of sign gesture names.
        
        Args:
            text: Natural English text (e.g., "Hello, how are you?")
        
        Returns:
            List of sign gesture names (e.g., ["WAVE_HELLO", "HOW", "BE", "POINT_FORWARD"])
        """
        if not text.strip():
            return []

        # Payload Normalization Pipeline (Self-Healing)
        if self._is_garbled(text):
            logger.warning(f"[Self-Healing] Garbled speech detected: '{text}'. Triggering clarification loop.")
            return ["CLARIFY_PLEASE"]

        # Try LLM for better phrase decomposition
        if self.client:
            try:
                # Provide bespoke dictionary data to the LLM context if available
                return await self._translate_with_llm(text, custom_dict)
            except Exception as e:
                logger.error(f"LLM translation failed: {e}. Using vocabulary fallback.")

        # Vocabulary-based fallback securely merges user config locally
        return self._translate_with_vocabulary(text, custom_dict)

    def _is_garbled(self, text: str) -> bool:
        """
        Self-Healing: Detects heavily garbled or non-parsable speech payloads.
        Returns True if the text appears to be noise or invalid STT reads.
        """
        cleaned = text.strip()
        if not cleaned:
            return True
            
        words = cleaned.split()
        if not words:
            return True
            
        # Analyze vowel presence as a heuristic for valid English words
        vowel_less_words = sum(1 for w in words if not any(v in w.lower() for v in 'aeiouy'))
        if vowel_less_words > len(words) * 0.5 and len(words) > 1:
            return True
            
        # Check for uncharacteristically long contiguous streams (spam/noise)
        if any(len(w) > 25 for w in words):
            return True
            
        return False

    async def _translate_with_llm(self, text: str, custom_dict: Optional[dict] = None) -> List[str]:
        """Use OpenAI to decompose text into sign gestures."""
        available_signs = ", ".join(sorted(set(SIGN_VOCABULARY.values())))
        
        system_prompt = f"""You are a spoken English to sign language translator.
Convert the given English text into a sequence of sign language gestures.

Available global signs: {available_signs}

Rules:
- Output ONLY a comma-separated list of sign names from the available list
- Sign language omits articles (the, a, an) and some prepositions
- Use the closest available sign for each concept
- Keep the sequence in a logical order for sign language grammar
- Sign language grammar is different: questions go at the end, time references at the beginning
"""
        if custom_dict:
            system_prompt += f"\n[User Bespoke Dictionary Override]:\n{custom_dict}\nMap these exactly if the concept matches."

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

    def _translate_with_vocabulary(self, text: str, custom_dict: Optional[dict] = None) -> List[str]:
        """Vocabulary-based translation (offline fallback) with non-polluting local dictionary merging."""
        # Securely merge custom_dict with SIGN_VOCABULARY for this request scope ONLY
        local_vocab = {**SIGN_VOCABULARY}
        if custom_dict:
            for k, v in custom_dict.items():
                local_vocab[k] = v[0] if isinstance(v, list) and v else v

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
                if phrase in local_vocab:
                    signs.append(local_vocab[phrase])
                    i += length
                    matched = True
                    break

            if not matched:
                word = words[i]
                if word not in SKIP_WORDS:
                    if word in local_vocab:
                        signs.append(local_vocab[word])
                    else:
                        # Fingerspell unknown words
                        signs.append(f"SPELL:{word.upper()}")
                i += 1

        logger.info(f"Vocabulary translation: '{text}' → {signs}")
        return signs if signs else ["CLARIFY_PLEASE"]

    def get_status(self) -> str:
        """Return engine status."""
        if self.client:
            return "openai-enhanced"
        return "vocabulary-based"
