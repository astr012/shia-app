'use client';

// ============================================================
// Shia — Transcript Log Component
// ============================================================

import { useRef, useEffect, useState, KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LogEntry } from '@/lib/types';

interface TranscriptLogProps {
  logs: LogEntry[];
  isActive: boolean;
  onManualInput: (text: string) => void;
}

export default function TranscriptLog({ logs, isActive, onManualInput }: TranscriptLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [inputValue, setInputValue] = useState('');

  // Auto-scroll to bottom when logs change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const handleSubmit = () => {
    if (inputValue.trim() && isActive) {
      onManualInput(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <h2 className="font-pixel text-2xl text-white">/// TRANSCRIPT_LOG</h2>

      <div className="bg-black border-2 border-white h-[500px] flex flex-col relative">
        {/* Scroll Area */}
        <div
          ref={scrollRef}
          className="flex-1 p-4 overflow-y-auto space-y-4 scrollbar-thin"
        >
          <AnimatePresence initial={false}>
            {logs.map((log) => (
              <motion.div
                key={log.id}
                className="text-sm leading-relaxed border-l-2 border-white/20 pl-3"
                initial={{ opacity: 0, x: -10, height: 0 }}
                animate={{ opacity: 1, x: 0, height: 'auto' }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-[10px] uppercase tracking-wider font-bold ${
                      log.source === 'USER'
                        ? 'text-matrix'
                        : log.source === 'AI'
                        ? 'text-cyan-400'
                        : 'text-purple-400'
                    }`}
                  >
                    [{log.source}]
                  </span>
                  <span className="text-[10px] text-gray-600 font-mono">{log.timestamp}</span>
                  {log.confidence !== undefined && (
                    <span className="text-[10px] text-matrix/60 font-mono">
                      CONF: {(log.confidence * 100).toFixed(1)}%
                    </span>
                  )}
                </div>
                <div
                  className={`font-mono ${
                    log.source === 'USER' ? 'text-white text-base' : 'text-gray-400'
                  }`}
                >
                  {log.text}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Active cursor */}
          {isActive && (
            <motion.div
              className="flex items-center gap-2 mt-4 text-matrix"
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
            >
              <span className="w-2 h-4 bg-matrix" />
              <span className="text-xs font-pixel">AWAITING INPUT...</span>
            </motion.div>
          )}
        </div>

        {/* Input Bar */}
        <div className="h-14 border-t-2 border-white flex items-center bg-[#111]">
          <div className="px-4 text-matrix font-bold font-mono">{'>'}</div>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="MANUAL OVERRIDE INPUT..."
            disabled={!isActive}
            className="flex-1 bg-transparent border-none outline-none text-white text-sm font-mono placeholder:text-gray-600 disabled:opacity-50"
          />
          <motion.button
            onClick={handleSubmit}
            disabled={!isActive || !inputValue.trim()}
            className="h-full px-4 border-l-2 border-white hover:bg-white hover:text-black font-pixel text-xl transition-colors disabled:opacity-50 cursor-pointer"
            whileHover={isActive && inputValue.trim() ? { backgroundColor: '#fff', color: '#000' } : {}}
            whileTap={isActive && inputValue.trim() ? { scale: 0.95 } : {}}
          >
            EXEC
          </motion.button>
        </div>
      </div>
    </div>
  );
}
