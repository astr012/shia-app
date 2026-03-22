'use client';

// ============================================================
// PIPELINE LAYER 3: Speech Processing (TTS + STT)
// Text-to-Speech: Synthesized output of translated sign language
// Speech-to-Text: Listening for spoken input to convert to sign
//
// Uses the native Web Speech API for zero-dependency operation.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';

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
  const [isSupported, setIsSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Check browser support
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      setIsSupported(!!SpeechRecognition);
    }
  }, []);

  const startListening = useCallback(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      onError?.('Speech recognition not supported in this browser');
      return;
    }

    // Create new recognition instance
    const recognition = new SpeechRecognition();
    recognition.continuous = continuous;
    recognition.interimResults = interimResults;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
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
      console.error('[STT] Error:', event.error);
      onError?.(event.error);
      if (event.error !== 'no-speech') {
        setIsListening(false);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      console.log('[STT] Listening ended');

      // Auto-restart if continuous mode is on
      if (continuous && recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch {
          // Already started or other error
        }
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

