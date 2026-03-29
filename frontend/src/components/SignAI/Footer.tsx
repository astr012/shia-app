'use client';

// ============================================================
// SHIA — Footer Component
// Shows version (live from backend when available), branding
// ============================================================

import { motion } from 'framer-motion';

interface FooterProps {
  serverVersion?: string;
  isServerReachable?: boolean;
}

export default function Footer({ serverVersion, isServerReachable }: FooterProps) {
  const displayVersion = serverVersion || '2.1.0-BETA';

  return (
    <footer className="max-w-7xl mx-auto mt-16 border-t border-white/10 pt-8 pb-6 flex flex-col md:flex-row justify-between items-center text-xs text-gray-600 gap-4">
      <div className="flex items-center gap-4">
        <motion.span
          className="uppercase font-bold tracking-widest text-gray-400 border border-gray-800 px-2 py-1 font-mono flex items-center gap-2 hover:border-[#00ff41]/50 transition-colors duration-150"
        >
          {isServerReachable && (
            <span className="w-1.5 h-1.5 rounded-full bg-matrix inline-block" />
          )}
          V {displayVersion.toUpperCase()}
        </motion.span>
        <span className="font-mono hidden sm:inline">ENCRYPTED.EDGE.COMPUTE</span>
        <span className="font-mono text-gray-700 hidden md:inline">•</span>
        <span className="font-mono text-gray-700 hidden md:inline">PRIVACY-FIRST PIPELINE</span>
      </div>
      <motion.div
        className="uppercase font-pixel text-sm text-gray-500"
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      >
        DESIGNED FOR UNIVERSAL ACCESSIBILITY
      </motion.div>
    </footer>
  );
}
