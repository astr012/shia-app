'use client';

// ============================================================
// Shia — App Header Component
// ============================================================

import { motion } from 'framer-motion';
import { Terminal, Power, RefreshCw, BarChart3 } from 'lucide-react';
import Link from 'next/link';
import { TranslationMode } from '@/lib/types';

interface HeaderProps {
  isSystemActive: boolean;
  mode: TranslationMode;
  onToggleMode: () => void;
  onToggleSystem: () => void;
}

export default function Header({ isSystemActive, mode, onToggleMode, onToggleSystem }: HeaderProps) {
  return (
    <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6 border-b-2 border-white/20 pb-6">
      {/* Logo + Status */}
      <div className="flex items-center gap-4">
        <motion.div
          className="w-12 h-12 bg-matrix flex items-center justify-center pixel-shadow border-2 border-black"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Terminal size={24} className="text-black" />
        </motion.div>
        <div>
          <h1 className="font-pixel text-4xl tracking-widest text-white uppercase">
            Shia
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <motion.div
              className={`w-3 h-3 border border-white ${
                isSystemActive ? 'bg-matrix' : 'bg-red-500'
              }`}
              animate={
                isSystemActive
                  ? { opacity: [1, 0, 1] }
                  : { opacity: 1 }
              }
              transition={{ duration: 1, repeat: Infinity, ease: 'linear', times: [0, 0.5, 1] }}
            />
            <span className="text-xs text-gray-400 font-mono">
              SYS.STATUS: {isSystemActive ? 'ONLINE & TRACKING' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4 w-full md:w-auto">
        <motion.button
          onClick={onToggleMode}
          className="flex-1 md:flex-none bg-transparent border-2 border-white text-white px-4 py-2 text-sm font-bold uppercase hover:bg-white hover:text-black transition-colors flex items-center justify-center gap-2 cursor-pointer"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          <motion.div
            animate={{ rotate: mode === 'SIGN_TO_SPEECH' ? 0 : 180 }}
            transition={{ duration: 0.3 }}
          >
            <RefreshCw size={16} />
          </motion.div>
          {mode === 'SIGN_TO_SPEECH' ? 'MODE: SGN → AUD' : 'MODE: AUD → SGN'}
        </motion.button>

        <Link href="/dashboard">
          <motion.div
            className="flex-1 md:flex-none bg-transparent border-2 border-white/30 text-gray-400 px-4 py-2 text-sm font-bold uppercase hover:bg-white/10 hover:text-white transition-colors flex items-center justify-center gap-2 cursor-pointer"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
          >
            <BarChart3 size={16} />
            DASHBOARD
          </motion.div>
        </Link>

        <motion.button
          onClick={onToggleSystem}
          className={`flex-1 md:flex-none border-2 border-black px-6 py-2 text-sm font-bold uppercase flex items-center justify-center gap-2 cursor-pointer ${
            isSystemActive
              ? 'bg-red-500 text-white shadow-[6px_6px_0px_0px_rgba(255,0,0,0.5)]'
              : 'bg-matrix text-black pixel-shadow'
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{
            scale: 0.97,
            x: 4,
            y: 4,
            boxShadow: '2px 2px 0px 0px rgba(0,255,65,0.8)',
          }}
        >
          <Power size={16} />
          {isSystemActive ? 'HALT' : 'INITIALIZE'}
        </motion.button>
      </div>
    </header>
  );
}
