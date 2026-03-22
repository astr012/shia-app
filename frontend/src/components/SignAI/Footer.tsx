'use client';

// ============================================================
// Shia — Footer Component
// ============================================================

import { motion } from 'framer-motion';

export default function Footer() {
  return (
    <footer className="max-w-7xl mx-auto mt-16 border-t border-white/10 pt-8 flex flex-col md:flex-row justify-between items-center text-xs text-gray-600 gap-4">
      <div className="flex items-center gap-4">
        <motion.span
          className="uppercase font-bold tracking-widest text-gray-400 border border-gray-800 px-2 py-1 font-mono"
          whileHover={{ borderColor: 'rgba(0,255,65,0.5)' }}
        >
          V 2.0.4-BETA
        </motion.span>
        <span className="font-mono">ENCRYPTED.EDGE.COMPUTE</span>
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
