'use client';

// ============================================================
// SignAI_OS — Quick Actions Grid Component
// ============================================================

import { motion } from 'framer-motion';
import { Volume2, Mic, Activity, Cpu } from 'lucide-react';

interface QuickActionsProps {
  isActive: boolean;
}

const ACTIONS = [
  {
    icon: Volume2,
    label: 'Audio Out',
    value: 'SYNTH_V2',
    valueColor: 'text-white',
  },
  {
    icon: Mic,
    label: 'Mic Input',
    value: 'ACTIVE',
    valueColor: 'text-matrix',
  },
  {
    icon: Activity,
    label: 'Latency',
    value: '12ms',
    valueColor: 'text-white',
  },
  {
    icon: Cpu,
    label: 'Compute',
    value: 'EDGE_WASM',
    valueColor: 'text-white',
  },
];

const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

export default function QuickActions({ isActive }: QuickActionsProps) {
  return (
    <motion.div
      className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {ACTIONS.map((action, idx) => {
        const Icon = action.icon;
        return (
          <motion.div
            key={action.label}
            className="border border-white/20 p-3 hover:bg-white/5 cursor-crosshair transition-colors group"
            variants={itemVariants}
            whileHover={{
              borderColor: 'rgba(0, 255, 65, 0.5)',
              transition: { duration: 0.15 },
            }}
          >
            <Icon
              size={16}
              className="text-gray-400 mb-2 group-hover:text-matrix transition-colors"
            />
            <div className="text-xs uppercase text-gray-500 font-bold">{action.label}</div>
            <div className={`text-sm font-pixel ${action.valueColor}`}>
              {isActive ? action.value : '—'}
            </div>
          </motion.div>
        );
      })}
    </motion.div>
  );
}
