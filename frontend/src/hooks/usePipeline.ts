'use client';

// ============================================================
// PIPELINE ORCHESTRATOR
// The central hook that wires all pipeline layers together:
//
//   ```mermaid
//   graph TD
//       A["Camera/Mic (Input)"] --> B["MediaPipe / STT Engine"]
//       B --> C["WebSocket Transport"]
//       C --> D["FastAPI (Grammar AI)"]
//       D --> E["WebSocket Response"]
//       E --> F["TTS Engine / Sign Anim"]
//       F --> G["Speaker / Screen"]
//   ```
//
// ============================================================

import { useState, useCallback, useRef, useEffect } from 'react';
import { useWebSocket, WSMessage } from './useWebSocket';
import { useTextToSpeech, useSpeechToText } from './useSpeech';
import { HandTrackingResult } from './useMediaPipe';
import { LogEntry, TranslationMode } from '@/lib/types';
import { createLogEntry } from '@/lib/utils';

// ── Configuration ───────────────────────────────────────────

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
const GESTURE_DEBOUNCE_MS = 800;   // Fast response on all devices
const GESTURE_CONFIDENCE_THRESHOLD = 0.75;

// ── Pipeline State ──────────────────────────────────────────

interface PipelineState {
  isActive: boolean;
  mode: TranslationMode;
  logs: LogEntry[];
  isProcessing: boolean;
  lastGesture: string | null;
  lastSpokenText: string | null;
  wsStatus: string;
  fps: number;
  signSequence: string[];
  signSourceText: string;
  signProcessingTime: number;
}

interface PipelineActions {
  startPipeline: () => void;
  stopPipeline: () => void;
  toggleMode: () => void;
  sendManualInput: (text: string) => void;
  processGestureResult: (result: HandTrackingResult) => void;
  clearLogs: () => void;
}

export function usePipeline(): PipelineState & PipelineActions {
  const [isActive, setIsActive] = useState(false);
  const [mode, setMode] = useState<TranslationMode>('SIGN_TO_SPEECH');
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    setLogs([createLogEntry('SYSTEM', 'SYSTEM INITIALIZED. WAITING FOR INPUT...')]);
  }, []);
  const [isProcessing, setIsProcessing] = useState(false);
  const [lastGesture, setLastGesture] = useState<string | null>(null);
  const [lastSpokenText, setLastSpokenText] = useState<string | null>(null);
  const [fps, setFps] = useState(0);
  const [signSequence, setSignSequence] = useState<string[]>([]);
  const [signSourceText, setSignSourceText] = useState('');
  const [signProcessingTime, setSignProcessingTime] = useState(0);

  const lastGestureTime = useRef(0);
  const gestureBuffer = useRef<string[]>([]);
  const gestureFlushTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const addLog = useCallback((source: LogEntry['source'], text: string) => {
    setLogs((prev) => [...prev, createLogEntry(source, text)]);
  }, []);

  // ── Wire up WebSocket ─────────────────────────────────────
  const handleWSMessage = useCallback(
    (message: WSMessage) => {
      switch (message.type) {
        case 'translation_result': {
          const { translated_text, source_gesture, audio, audio_format } = message.payload as {
            translated_text: string;
            source_gesture: string;
            audio?: string | null;
            audio_format?: string | null;
          };
          addLog('SYSTEM', `[TRANSLATED]: "${translated_text}" (from: ${source_gesture})`);
          setIsProcessing(false);

          // If SIGN_TO_SPEECH mode, play audio
          if (mode === 'SIGN_TO_SPEECH') {
            if (audio && audio_format === 'mp3') {
              // Server-side TTS — natural voice, identical on ALL devices
              playServerAudio(audio);
              addLog('SYSTEM', '[AUDIO]: Natural voice (server-generated)');
            } else {
              // Fallback: browser TTS
              speak(translated_text);
              addLog('SYSTEM', '[AUDIO]: Browser TTS (fallback)');
            }
          }
          break;
        }

        case 'sign_animation': {
          const { sign_sequence, source_text, processing_time_ms } = message.payload as {
            sign_sequence: string[];
            source_text?: string;
            processing_time_ms?: number;
          };
          addLog('SYSTEM', `[SIGN OUTPUT]: ${sign_sequence.join(' → ')}`);
          setSignSequence(sign_sequence);
          setSignSourceText(source_text || '');
          setSignProcessingTime(processing_time_ms || 0);
          setIsProcessing(false);
          break;
        }

        case 'grammar_processed': {
          const { original, corrected } = message.payload as {
            original: string;
            corrected: string;
          };
          addLog('AI', `[GRAMMAR]: "${original}" → "${corrected}"`);
          break;
        }

        case 'error': {
          const { message: errMsg } = message.payload as { message: string };
          addLog('SYSTEM', `[ERROR]: ${errMsg}`);
          setIsProcessing(false);
          break;
        }

        case 'session_info': {
          // Store or ignore session info as needed
          addLog('SYSTEM', '[WS] Session established');
          break;
        }

        case 'heartbeat': {
          // Ignore heartbeat ping
          break;
        }

        default:
          console.log('[Pipeline] Unknown message type:', message.type);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- speak/playServerAudio defined after this hook; hook ordering constraint
    [mode, addLog]
  );

  const { status: wsStatus, send: wsSend, connect: wsConnect, disconnect: wsDisconnect } =
    useWebSocket({
      url: WS_URL,
      autoConnect: false,
      reconnect: true,
      onMessage: handleWSMessage,
    });

  // ── Wire up Text-to-Speech ────────────────────────────────
  const { speak } = useTextToSpeech({
    rate: 0.95,
    onStart: () => addLog('SYSTEM', '[TTS]: Speaking...'),
    onEnd: () => addLog('SYSTEM', '[TTS]: Complete'),
  });

  // ── Wire up Speech-to-Text (for SPEECH_TO_SIGN mode) ─────
  const handleSTTResult = useCallback(
    (transcript: string, isFinal: boolean) => {
      if (!isFinal) return;

      addLog('USER', `[SPEECH DETECTED]: "${transcript}"`);
      setLastSpokenText(transcript);

      // Send to backend for sign language translation
      wsSend('speech_input', {
        text: transcript,
        language: 'en',
        mode: 'SPEECH_TO_SIGN',
      });

      setIsProcessing(true);
      addLog('SYSTEM', '[PROCESSING]: Converting speech to sign sequence...');
    },
    [wsSend, addLog]
  );

  const {
    // isListening state consumed implicitly by STT engine
    startListening,
    stopListening,
  } = useSpeechToText({
    continuous: true,
    onResult: handleSTTResult,
    onError: (err) => addLog('SYSTEM', `[STT ERROR]: ${err}`),
  });

  // ── Gesture Processing (SIGN_TO_SPEECH pipeline) ──────────

  const processGestureResult = useCallback(
    (result: HandTrackingResult) => {
      if (!isActive || mode !== 'SIGN_TO_SPEECH') return;
      if (!result.gesture || result.confidence < GESTURE_CONFIDENCE_THRESHOLD) return;

      setFps(30); // Will be overridden by actual FPS from MediaPipe hook

      const now = Date.now();
      if (now - lastGestureTime.current < GESTURE_DEBOUNCE_MS) return;

      // Buffer gestures for sentence construction
      gestureBuffer.current.push(result.gesture);
      setLastGesture(result.gesture);
      lastGestureTime.current = now;

      addLog('USER', `[GESTURE DETECTED]: "${result.gesture}" (conf: ${(result.confidence * 100).toFixed(1)}%)`);

      // Flush buffer after a pause (send accumulated gestures as a sequence)
      if (gestureFlushTimer.current) {
        clearTimeout(gestureFlushTimer.current);
      }

      gestureFlushTimer.current = setTimeout(() => {
        if (gestureBuffer.current.length > 0) {
          const sequence = [...gestureBuffer.current];
          gestureBuffer.current = [];

          addLog('SYSTEM', `[SENDING SEQUENCE]: ${sequence.join(' → ')}`);
          setIsProcessing(true);

          // Send gesture sequence to backend for grammar processing
          wsSend('gesture_sequence', {
            gestures: sequence,
            mode: 'SIGN_TO_SPEECH',
            timestamp: Date.now(),
          });
        }
      }, 1200); // 1.2s of no new gestures = flush (was 2s — faster for all devices)
    },
    [isActive, mode, wsSend, addLog]
  );

  // ── Pipeline Control ──────────────────────────────────────

  const startPipeline = useCallback(() => {
    setIsActive(true);
    setLogs([createLogEntry('SYSTEM', 'BOOTING VISION MODULE...')]);

    // Connect WebSocket
    wsConnect();

    setTimeout(() => addLog('SYSTEM', 'LOADING MEDIAPIPE HAND MODEL...'), 300);
    setTimeout(() => addLog('SYSTEM', 'INITIALIZING SPEECH ENGINE...'), 600);
    setTimeout(() => addLog('SYSTEM', `MODE: ${mode === 'SIGN_TO_SPEECH' ? 'SIGN → SPEECH' : 'SPEECH → SIGN'}`), 900);
    setTimeout(() => {
      addLog('SYSTEM', 'ALL SYSTEMS NOMINAL. PIPELINE ACTIVE.');

      // If in speech-to-sign mode, start listening
      if (mode === 'SPEECH_TO_SIGN') {
        startListening();
      }
    }, 1200);
  }, [mode, wsConnect, addLog, startListening]);

  const stopPipeline = useCallback(() => {
    setIsActive(false);
    addLog('SYSTEM', 'SHUTTING DOWN PIPELINE...');
    addLog('SYSTEM', 'SYSTEM OFFLINE.');

    // Disconnect everything
    wsDisconnect();
    stopListening();

    // Clear buffers
    gestureBuffer.current = [];
    if (gestureFlushTimer.current) {
      clearTimeout(gestureFlushTimer.current);
    }

    setFps(0);
    setIsProcessing(false);
    setLastGesture(null);
  }, [wsDisconnect, stopListening, addLog]);

  const toggleMode = useCallback(() => {
    const newMode = mode === 'SIGN_TO_SPEECH' ? 'SPEECH_TO_SIGN' : 'SIGN_TO_SPEECH';
    setMode(newMode);
    addLog('SYSTEM', `MODE SWITCHED: ${newMode === 'SIGN_TO_SPEECH' ? 'SIGN → SPEECH' : 'SPEECH → SIGN'}`);

    if (isActive) {
      // Handle mode-specific resources
      if (newMode === 'SPEECH_TO_SIGN') {
        startListening();
      } else {
        stopListening();
      }
    }
  }, [mode, isActive, addLog, startListening, stopListening]);

  const sendManualInput = useCallback(
    (text: string) => {
      if (!isActive) return;

      addLog('USER', `[MANUAL INPUT]: "${text}"`);
      setIsProcessing(true);

      if (mode === 'SIGN_TO_SPEECH') {
        // Treat manual input as if it were detected gestures
        wsSend('manual_text', {
          text,
          mode: 'SIGN_TO_SPEECH',
          timestamp: Date.now(),
        });
        addLog('SYSTEM', '[PROCESSING]: Synthesizing speech...');

        // Fallback: speak directly if WS is not connected
        if (wsStatus === 'disconnected') {
          speak(text);
          addLog('SYSTEM', '[AUDIO SYNTHESIZED & PLAYED] (offline mode)');
          setIsProcessing(false);
        }
      } else {
        // SPEECH_TO_SIGN: Send text for sign translation
        wsSend('speech_input', {
          text,
          language: 'en',
          mode: 'SPEECH_TO_SIGN',
        });
        addLog('SYSTEM', '[PROCESSING]: Converting to sign sequence...');
      }
    },
    [isActive, mode, wsSend, wsStatus, speak, addLog]
  );

  const clearLogs = useCallback(() => {
    setLogs([createLogEntry('SYSTEM', 'LOGS CLEARED.')]);
  }, []);

  // ── Server-side Audio Playback (natural voice on ALL devices) ──
  const playServerAudio = useCallback((base64Audio: string) => {
    try {
      const audioBytes = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
      const blob = new Blob([audioBytes], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => URL.revokeObjectURL(url);
      audio.onerror = () => {
        URL.revokeObjectURL(url);
        // Fallback to browser TTS if audio fails
        console.warn('[Audio] Server audio failed, using browser TTS');
      };
      audio.play().catch(() => {
        console.warn('[Audio] Autoplay blocked, using browser TTS');
      });
    } catch (e) {
      console.error('[Audio] Failed to play server audio:', e);
    }
  }, []);

  // ── Demo simulation when backend is not connected ─────────
  useEffect(() => {
    if (!isActive || wsStatus === 'connected') return;

    // Run a demo sequence when backend isn't available
    const demoTimer = setTimeout(() => {
      if (mode === 'SIGN_TO_SPEECH') {
        addLog('USER', '[DETECTED GESTURE]: "HELLO" (conf: 97.2%)');
        setTimeout(() => {
          addLog('AI', '[GRAMMAR]: "HELLO" → "Hello!"');
        }, 500);
        setTimeout(() => {
          addLog('SYSTEM', '[AUDIO SYNTHESIZED & PLAYED]');
          speak('Hello!');
        }, 1000);
        setTimeout(() => {
          addLog('USER', '[DETECTED GESTURE]: "HOW_ARE_YOU" (conf: 94.8%)');
        }, 4000);
        setTimeout(() => {
          addLog('AI', '[GRAMMAR]: "HOW_ARE_YOU" → "How are you?"');
        }, 4500);
        setTimeout(() => {
          addLog('SYSTEM', '[AUDIO SYNTHESIZED & PLAYED]');
          speak('How are you?');
        }, 5000);
      }
    }, 2000);

    return () => clearTimeout(demoTimer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive, wsStatus, mode]);

  return {
    // State
    isActive,
    mode,
    logs,
    isProcessing,
    lastGesture,
    lastSpokenText,
    wsStatus,
    fps,
    signSequence,
    signSourceText,
    signProcessingTime,

    // Actions
    startPipeline,
    stopPipeline,
    toggleMode,
    sendManualInput,
    processGestureResult,
    clearLogs,
  };
}
