'use client';

// ============================================================
// SignAI_OS — Sign Player Component
//
// Visual sign-token renderer that animates sign language
// gesture sequences received from the backend WebSocket.
// Renders tokens as an animated sequence with timing,
// confidence display, and unknown token fallback styling.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Hand, Play, Pause, SkipForward, Volume2 } from 'lucide-react';

// ── Sign token metadata ──────────────────────────────────────

interface SignToken {
  label: string;
  type: 'known' | 'spelled' | 'unknown';
  durationMs: number;
}

interface SignPlayerProps {
  signSequence: string[];
  sourceText?: string;
  processingTimeMs?: number;
  isVisible: boolean;
}

// Gesture label → visual emoji/icon mapping
const GESTURE_ICONS: Record<string, string> = {
  WAVE_HELLO: '👋', HELLO: '👋', HI: '👋',
  HOW: '🤔', HOW_ARE_YOU: '🤔',
  BE: '🫵', POINT_FORWARD: '👉', POINT_YOU: '👉',
  POINT: '☝️', POINT_UP: '☝️', POINT_DOWN: '👇',
  YES: '👍', NO: '🙅', THUMBS_UP: '👍', THUMBS_DOWN: '👎',
  THANK_YOU: '🙏', THANKS: '🙏', PLEASE: '🤲',
  HELP: '🆘', SORRY: '😔', LOVE: '❤️', I_LOVE_YOU: '🤟',
  GOOD: '👌', BAD: '👎', OK_SIGN: '👌',
  WANT: '🫳', NEED: '🫳', EAT: '🍽️', FOOD: '🍽️',
  DRINK: '🥤', WATER: '💧', STOP: '✋', GO: '🏃',
  COME: '🫴', HAPPY: '😊', SAD: '😢', MORE: '🤌',
  WHAT: '❓', WHERE: '📍', WHO: '👤', WHEN: '⏰', WHY: '❓',
  NAME: '📛', MY: '🫵', YOUR: '👉',
  FAMILY: '👨‍👩‍👧‍👦', FRIEND: '🤝', SCHOOL: '🏫', WORK: '💼', HOME: '🏠',
  FIST: '✊', PEACE: '✌️', TWO: '✌️', THREE: '🤟', FOUR: '🖖',
  OPEN_PALM: '🖐️', CALL_ME: '🤙', PINCH: '🤏', SNAP: '🫰',
  HORNS: '🤘', W_SIGN: '🤟', LETTER_A: '🅰️',
};

// Parse sign sequence into tokens with timing
function parseTokens(sequence: string[]): SignToken[] {
  return sequence.map((label) => {
    const upper = label.toUpperCase();
    if (upper.startsWith('SPELL:')) {
      return { label, type: 'spelled' as const, durationMs: 1200 };
    }
    if (GESTURE_ICONS[upper] || upper.includes('_')) {
      return { label, type: 'known' as const, durationMs: 800 };
    }
    return { label, type: 'unknown' as const, durationMs: 600 };
  });
}

// ── Main Component ───────────────────────────────────────────

export default function SignPlayer({ signSequence, sourceText, processingTimeMs, isVisible }: SignPlayerProps) {
  const [tokens, setTokens] = useState<SignToken[]>([]);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasFinished, setHasFinished] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Parse tokens when sequence changes
  const parsedTokens = signSequence.length > 0 ? parseTokens(signSequence) : tokens;
  if (signSequence.length > 0 && parsedTokens !== tokens && JSON.stringify(parsedTokens) !== JSON.stringify(tokens)) {
    setTokens(parsedTokens);
    setCurrentIndex(-1);
    setHasFinished(false);
    setIsPlaying(true);
  }

  // Playback engine
  const advanceToken = useCallback(() => {
    setCurrentIndex((prev) => {
      const next = prev + 1;
      if (next >= tokens.length) {
        setIsPlaying(false);
        setHasFinished(true);
        return prev;
      }
      return next;
    });
  }, [tokens.length]);

  useEffect(() => {
    if (!isPlaying || tokens.length === 0) return;

    // Start from beginning if not started
    if (currentIndex === -1) {
      // Use timeout to avoid synchronous setState cascade
      const startTimer = setTimeout(() => setCurrentIndex(0), 0);
      return () => clearTimeout(startTimer);
    }

    const currentToken = tokens[currentIndex];
    if (!currentToken) return;

    timerRef.current = setTimeout(() => {
      advanceToken();
    }, currentToken.durationMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isPlaying, currentIndex, tokens, advanceToken]);

  // Controls
  const handlePlayPause = () => {
    if (hasFinished) {
      setCurrentIndex(-1);
      setHasFinished(false);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleSkip = () => {
    if (currentIndex < tokens.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  if (!isVisible || tokens.length === 0) return null;

  const activeToken = currentIndex >= 0 && currentIndex < tokens.length ? tokens[currentIndex] : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="border-2 border-matrix/30 bg-black/80 p-4 mt-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Hand size={16} className="text-matrix" />
          <span className="font-pixel text-sm text-matrix tracking-wider uppercase">Sign Player</span>
        </div>
        <div className="flex items-center gap-2">
          <motion.button
            onClick={handlePlayPause}
            className="p-1.5 border border-white/20 text-gray-400 hover:text-white hover:border-white/40 transition-colors cursor-pointer"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
          >
            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
          </motion.button>
          <motion.button
            onClick={handleSkip}
            className="p-1.5 border border-white/20 text-gray-400 hover:text-white hover:border-white/40 transition-colors cursor-pointer"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            disabled={currentIndex >= tokens.length - 1}
          >
            <SkipForward size={14} />
          </motion.button>
        </div>
      </div>

      {/* Source text */}
      {sourceText && (
        <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/10">
          <Volume2 size={12} className="text-gray-500" />
          <span className="font-mono text-xs text-gray-400 italic">&ldquo;{sourceText}&rdquo;</span>
          {processingTimeMs !== undefined && (
            <span className="font-mono text-[10px] text-gray-600 ml-auto">{processingTimeMs.toFixed(1)}ms</span>
          )}
        </div>
      )}

      {/* Active Token Display */}
      <div className="flex items-center justify-center min-h-[100px] mb-4 relative">
        <AnimatePresence mode="wait">
          {activeToken ? (
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, scale: 0.5, rotateY: 90 }}
              animate={{ opacity: 1, scale: 1, rotateY: 0 }}
              exit={{ opacity: 0, scale: 0.5, rotateY: -90 }}
              transition={{ duration: 0.3, type: 'spring', stiffness: 200 }}
              className="flex flex-col items-center gap-2"
            >
              {/* Gesture icon */}
              <div className={`text-5xl ${activeToken.type === 'spelled' ? 'font-pixel' : ''}`}>
                {activeToken.type === 'spelled' ? (
                  <span className="text-yellow-400 font-pixel text-4xl tracking-[0.5em]">
                    {activeToken.label.replace('SPELL:', '')}
                  </span>
                ) : (
                  GESTURE_ICONS[activeToken.label.toUpperCase()] || '🤟'
                )}
              </div>
              {/* Label */}
              <span className={`font-pixel text-lg tracking-wider uppercase ${
                activeToken.type === 'known' ? 'text-matrix' :
                activeToken.type === 'spelled' ? 'text-yellow-400' :
                'text-gray-400'
              }`}>
                {activeToken.label.replace('SPELL:', '').replace(/_/g, ' ')}
              </span>
              {/* Type badge */}
              <span className={`text-[10px] font-mono px-2 py-0.5 border ${
                activeToken.type === 'known' ? 'border-matrix/30 text-matrix/60' :
                activeToken.type === 'spelled' ? 'border-yellow-400/30 text-yellow-400/60' :
                'border-gray-600 text-gray-500'
              }`}>
                {activeToken.type === 'spelled' ? 'FINGERSPELL' : activeToken.type.toUpperCase()}
              </span>
            </motion.div>
          ) : hasFinished ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center"
            >
              <span className="font-pixel text-sm text-gray-500">SEQUENCE COMPLETE</span>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center"
            >
              <span className="font-pixel text-sm text-gray-600 animate-blink">READY</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Token Timeline */}
      <div className="flex gap-1 flex-wrap">
        {tokens.map((token, i) => (
          <motion.div
            key={i}
            className={`px-2 py-1 text-[10px] font-mono border transition-all cursor-default ${
              i === currentIndex
                ? 'border-matrix bg-matrix/20 text-matrix scale-105'
                : i < currentIndex
                ? 'border-matrix/20 text-matrix/40 bg-matrix/5'
                : 'border-white/10 text-gray-600'
            }`}
            animate={i === currentIndex ? { scale: [1, 1.05, 1] } : {}}
            transition={{ duration: 0.5, repeat: i === currentIndex ? Infinity : 0 }}
          >
            {token.type === 'spelled'
              ? `✋ ${token.label.replace('SPELL:', '')}`
              : (GESTURE_ICONS[token.label.toUpperCase()] || '•') + ' ' + token.label.replace(/_/g, ' ')}
          </motion.div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="mt-3 h-1 bg-white/5 overflow-hidden">
        <motion.div
          className="h-full bg-matrix"
          animate={{ width: `${tokens.length > 0 ? ((currentIndex + 1) / tokens.length) * 100 : 0}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
    </motion.div>
  );
}
