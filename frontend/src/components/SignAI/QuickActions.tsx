'use client';

// ============================================================
// SHIA — Quick Actions Grid Component
// Live system telemetry tiles showing real backend metrics
// ============================================================

import { motion } from 'framer-motion';
import { Volume2, Mic, Activity, Cpu, Wifi, WifiOff, Zap, Clock } from 'lucide-react';

interface QuickActionsProps {
  isActive: boolean;
  wsStatus: string;
  latencyMs: number;
  isServerReachable: boolean;
  grammarEngine: string;
  translationEngine: string;
  activeConnections: number;
  serverUptime: string;
}

const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.08 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0 },
};

function getLatencyColor(ms: number): string {
  if (ms === 0) return 'text-gray-500';
  if (ms < 50) return 'text-matrix';
  if (ms < 150) return 'text-yellow-400';
  return 'text-red-400';
}

function getWsStatusDisplay(status: string): { label: string; color: string } {
  switch (status) {
    case 'connected':
      return { label: 'LINKED', color: 'text-matrix' };
    case 'connecting':
      return { label: 'SYNC...', color: 'text-yellow-400' };
    case 'error':
      return { label: 'ERROR', color: 'text-red-400' };
    default:
      return { label: 'OFFLINE', color: 'text-gray-500' };
  }
}

export default function QuickActions({
  isActive,
  wsStatus,
  latencyMs,
  isServerReachable,
  grammarEngine,
  translationEngine,
  activeConnections,
  serverUptime,
}: QuickActionsProps) {
  const wsDisplay = getWsStatusDisplay(wsStatus);

  const TILES = [
    {
      icon: isServerReachable ? Wifi : WifiOff,
      label: 'Backend',
      value: isActive ? (isServerReachable ? 'ONLINE' : 'OFFLINE') : '—',
      valueColor: isActive ? (isServerReachable ? 'text-matrix' : 'text-red-400') : 'text-gray-500',
      subtext: isActive && isServerReachable ? serverUptime : undefined,
    },
    {
      icon: Zap,
      label: 'WebSocket',
      value: isActive ? wsDisplay.label : '—',
      valueColor: isActive ? wsDisplay.color : 'text-gray-500',
      subtext: isActive && activeConnections > 0 ? `${activeConnections} conn` : undefined,
    },
    {
      icon: Activity,
      label: 'Latency',
      value: isActive ? (latencyMs > 0 ? `${latencyMs}ms` : '—') : '—',
      valueColor: isActive ? getLatencyColor(latencyMs) : 'text-gray-500',
      subtext: isActive && latencyMs > 0 ? (latencyMs < 50 ? 'OPTIMAL' : latencyMs < 150 ? 'MODERATE' : 'HIGH') : undefined,
    },
    {
      icon: Cpu,
      label: 'Grammar AI',
      value: isActive ? (grammarEngine.includes('openai') ? 'GPT-4o' : 'RULES') : '—',
      valueColor: isActive ? (grammarEngine.includes('openai') ? 'text-cyan-400' : 'text-white') : 'text-gray-500',
      subtext: isActive ? (grammarEngine.includes('openai') ? 'LLM' : 'OFFLINE') : undefined,
    },
    {
      icon: Volume2,
      label: 'Audio Out',
      value: isActive ? 'WEB_TTS' : '—',
      valueColor: isActive ? 'text-white' : 'text-gray-500',
      subtext: isActive ? 'BROWSER' : undefined,
    },
    {
      icon: Mic,
      label: 'Mic Input',
      value: isActive ? 'WEB_STT' : '—',
      valueColor: isActive ? 'text-matrix' : 'text-gray-500',
      subtext: isActive ? 'BROWSER' : undefined,
    },
    {
      icon: Clock,
      label: 'Translate',
      value: isActive ? (translationEngine.includes('openai') ? 'LLM+VOC' : 'VOCAB') : '—',
      valueColor: isActive ? (translationEngine.includes('openai') ? 'text-cyan-400' : 'text-white') : 'text-gray-500',
      subtext: isActive ? `${translationEngine.includes('openai') ? 'AI' : 'LOCAL'}` : undefined,
    },
    {
      icon: Cpu,
      label: 'Compute',
      value: isActive ? 'EDGE' : '—',
      valueColor: isActive ? 'text-white' : 'text-gray-500',
      subtext: isActive ? 'WASM' : undefined,
    },
  ];

  return (
    <motion.div
      className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {TILES.map((tile) => {
        const Icon = tile.icon;
        return (
          <motion.div
            key={tile.label}
            className="border border-white/20 p-3 hover:bg-white/5 cursor-crosshair transition-colors group relative overflow-hidden"
            variants={itemVariants}
            whileHover={{
              borderColor: 'rgba(0, 255, 65, 0.5)',
              transition: { duration: 0.15 },
            }}
          >
            {/* Pulse indicator for active tiles */}
            {isActive && tile.value !== '—' && (
              <motion.div
                className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-matrix"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            )}

            <Icon
              size={14}
              className="text-gray-500 mb-2 group-hover:text-matrix transition-colors"
            />
            <div className="text-[10px] uppercase text-gray-600 font-bold tracking-wider">
              {tile.label}
            </div>
            <div className={`text-sm font-pixel ${tile.valueColor} mt-0.5`}>
              {tile.value}
            </div>
            {tile.subtext && (
              <div className="text-[9px] text-gray-600 font-mono mt-0.5 uppercase">
                {tile.subtext}
              </div>
            )}
          </motion.div>
        );
      })}
    </motion.div>
  );
}
