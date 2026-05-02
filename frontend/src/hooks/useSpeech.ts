'use client';

// ============================================================
// PIPELINE LAYER 3: Speech Processing (TTS + STT)
// Text-to-Speech: Synthesized output of translated sign language
// Speech-to-Text: Listening for spoken input to convert to sign
//
// Uses the native Web Speech API for zero-dependency operation.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';

// Module-scope constant — stable reference, no dependency churn
const FATAL_ERRORS = ['network', 'not-allowed', 'service-not-allowed', 'language-not-supported'] as const;

// ── TEXT-TO-SPEECH ──────────────────────────────────────────

interface UseTTSOptions {
  voice?: string;
  rate?: number;
  pitch?: number;
  volume?: number;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: string) => void;
}

interface UseTTSReturn {
  speak: (text: string) => void;
  cancel: () => void;
  isSpeaking: boolean;
  voices: SpeechSynthesisVoice[];
  selectedVoice: SpeechSynthesisVoice | null;
  setVoiceByName: (name: string) => void;
}

export function useTextToSpeech({
  voice,
  rate = 1.0,
  pitch = 1.0,
  volume = 1.0,
  onStart,
  onEnd,
  onError,
}: UseTTSOptions = {}): UseTTSReturn {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<SpeechSynthesisVoice | null>(null);

  // Load available voices
  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const loadVoices = () => {
      const availableVoices = window.speechSynthesis.getVoices();
      setVoices(availableVoices);

      // Auto-select voice
      if (voice) {
        const match = availableVoices.find(
          (v) => v.name.toLowerCase().includes(voice.toLowerCase())
        );
        if (match) setSelectedVoice(match);
      } else {
        // Default to first English voice
        const englishVoice = availableVoices.find((v) => v.lang.startsWith('en'));
        if (englishVoice) setSelectedVoice(englishVoice);
      }
    };

    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;

    return () => {
      window.speechSynthesis.onvoiceschanged = null;
    };
  }, [voice]);

  const speak = useCallback(
    (text: string) => {
      if (typeof window === 'undefined' || !window.speechSynthesis) {
        onError?.('Speech synthesis not supported');
        return;
      }

      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      if (selectedVoice) utterance.voice = selectedVoice;
      utterance.rate = rate;
      utterance.pitch = pitch;
      utterance.volume = volume;

      utterance.onstart = () => {
        setIsSpeaking(true);
        onStart?.();
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        onEnd?.();
      };

      utterance.onerror = (e) => {
        setIsSpeaking(false);
        onError?.(e.error);
      };

      window.speechSynthesis.speak(utterance);
    },
    [selectedVoice, rate, pitch, volume, onStart, onEnd, onError]
  );

  const cancel = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const setVoiceByName = useCallback(
    (name: string) => {
      const match = voices.find((v) => v.name === name);
      if (match) setSelectedVoice(match);
    },
    [voices]
  );

  return { speak, cancel, isSpeaking, voices, selectedVoice, setVoiceByName };
}

// ── SPEECH-TO-TEXT ──────────────────────────────────────────

interface UseSTTOptions {
  continuous?: boolean;
  interimResults?: boolean;
  language?: string;
  onResult?: (transcript: string, isFinal: boolean) => void;
  onError?: (error: string) => void;
}

interface UseSTTReturn {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  startListening: () => void;
  stopListening: () => void;
  isSupported: boolean;
}

export function useSpeechToText({
  continuous = true,
  interimResults = true,
  language = 'en-US',
  onResult,
  onError,
}: UseSTTOptions = {}): UseSTTReturn {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isSupported] = useState(() => {
    if (typeof window === 'undefined') return false;
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  });
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Retry state to prevent infinite error loops on ALL devices
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hadFatalError = useRef(false);
  const intentionalStop = useRef(false);

  const MAX_RETRIES = 3;

  const startListening = useCallback(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      onError?.('Speech recognition not supported in this browser');
      return;
    }

    // Reset state for fresh start
    hadFatalError.current = false;
    retryCount.current = 0;
    intentionalStop.current = false;

    // Create new recognition instance
    const recognition = new SpeechRecognition();
    recognition.continuous = continuous;
    recognition.interimResults = interimResults;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
      retryCount.current = 0; // Reset retries on successful start
      console.log('[STT] Listening started');
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let finalTranscript = '';
      let interim = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalTranscript += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (finalTranscript) {
        setTranscript((prev) => prev + finalTranscript);
        onResult?.(finalTranscript, true);
      }

      setInterimTranscript(interim);
      if (interim) {
        onResult?.(interim, false);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const err = event.error;

      // Fatal errors: stop retrying entirely
      if ((FATAL_ERRORS as readonly string[]).includes(err)) {
        hadFatalError.current = true;
        setIsListening(false);

        if (err === 'network') {
          console.warn('[STT] Network error — requires internet and Google API access for Chrome Speech API. Stopping retries.');
          onError?.('Speech recognition requires Google API access. Please use standard Google Chrome or Edge. Brave/Chromium often block this. If using Chrome, check ad-blockers. Alternatively, use manual text input.');
        } else if (err === 'not-allowed') {
          console.warn('[STT] Microphone permission denied.');
          onError?.('Microphone access denied. Please allow microphone in browser settings.');
        } else {
          console.error('[STT] Fatal error:', err);
          onError?.(err);
        }
        return;
      }

      // Non-fatal errors (no-speech, aborted): just log, don't stop
      if (err === 'no-speech') {
        // Totally normal — user just isn't speaking. Don't spam errors.
        return;
      }

      console.warn('[STT] Non-fatal error:', err);
      onError?.(err);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);

      // Don't restart if: intentionally stopped, fatal error, or max retries exceeded
      if (intentionalStop.current || hadFatalError.current) {
        console.log('[STT] Stopped (intentional or fatal error).');
        return;
      }

      // Auto-restart with exponential backoff
      if (continuous && recognitionRef.current) {
        if (retryCount.current >= MAX_RETRIES) {
          console.warn(`[STT] Max retries (${MAX_RETRIES}) exceeded. Stopping.`);
          onError?.('Speech recognition stopped after multiple failures. Click to retry.');
          return;
        }

        const backoffMs = Math.min(1000 * Math.pow(2, retryCount.current), 8000);
        retryCount.current++;
        console.log(`[STT] Restarting in ${backoffMs}ms (attempt ${retryCount.current}/${MAX_RETRIES})`);

        retryTimer.current = setTimeout(() => {
          if (recognitionRef.current && !intentionalStop.current && !hadFatalError.current) {
            try {
              recognitionRef.current.start();
            } catch {
              // Already started or destroyed
            }
          }
        }, backoffMs);
      }
    };

    recognitionRef.current = recognition;

    try {
      recognition.start();
    } catch {
      onError?.('Failed to start speech recognition');
    }
  }, [continuous, interimResults, language, onResult, onError]);

  const stopListening = useCallback(() => {
    intentionalStop.current = true;
    hadFatalError.current = false;

    if (retryTimer.current) {
      clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
    setInterimTranscript('');
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      intentionalStop.current = true;
      if (retryTimer.current) {
        clearTimeout(retryTimer.current);
      }
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
    };
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    isSupported,
  };
}

