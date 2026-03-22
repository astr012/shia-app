'use client';

// ============================================================
// SHIA — System Dashboard
// Live command center showing analytics, cache, sessions,
// vocabulary stats, and system health from backend APIs
// ============================================================

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import {
  Terminal, ArrowLeft, Activity, Database, Zap, Clock,
  Users, Cpu, RefreshCw, Trash2, BarChart3, BookOpen,
  Wifi, WifiOff, TrendingUp,
} from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Types ───────────────────────────────────────────────────

interface HealthData {
  status: string;
  version: string;
  uptime: string;
  timestamp: string;
  services: {
    grammar_engine: string;
    translation_engine: string;
    active_connections: number;
    active_sessions: number;
    cache: {
      grammar_entries: number;
      sign_entries: number;
      total_entries: number;
      max_size_per_type: number;
      ttl_seconds: number;
      hits: number;
      misses: number;
      hit_rate_pct: number;
    };
  };
  config: {
    app: string;
    version: string;
    environment: string;
    openai_configured: boolean;
    openai_model: string | null;
  };
}

interface AnalyticsData {
  uptime_seconds: number;
  uptime_formatted: string;
  total_translations: number;
  total_sign_conversions: number;
  total_errors: number;
  active_sessions: number;
  avg_latency_ms: Record<string, number>;
  cache: {
    grammar_entries: number;
    sign_entries: number;
    total_entries: number;
    max_size_per_type: number;
    ttl_seconds: number;
    hits: number;
    misses: number;
    hit_rate_pct: number;
  };
  rate_limiter: {
    active_clients: number;
    total_denied: number;
  };
}

interface VocabData {
  vocabulary: Record<string, string>;
  skip_words: string[];
  total_signs: number;
  total_words: number;
}

interface SessionData {
  active_sessions: number;
  sessions: Array<{
    session_id: string;
    mode: string;
    connected_at: string;
    duration: string;
    gestures: number;
    speeches: number;
    manual_inputs: number;
    errors: number;
  }>;
}

// ── Helper Components ───────────────────────────────────────

function StatCard({
  icon: Icon, label, value, sub, color = 'text-matrix', delay = 0,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
  delay?: number;
}) {
  return (
    <motion.div
      className="border border-white/15 bg-black/40 p-5 relative overflow-hidden group hover:border-matrix/40 transition-colors"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      whileHover={{ borderColor: 'rgba(0,255,65,0.4)' }}
    >
      <div className="absolute top-3 right-3 opacity-10 group-hover:opacity-20 transition-opacity">
        <Icon size={40} />
      </div>
      <Icon size={16} className="text-gray-500 mb-2" />
      <div className="text-[10px] uppercase text-gray-500 tracking-wider font-bold">{label}</div>
      <div className={`text-2xl font-pixel ${color} mt-1`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-600 font-mono mt-1">{sub}</div>}
    </motion.div>
  );
}

function SectionHeader({ title, icon: Icon }: { title: string; icon: React.ComponentType<{ size?: number; className?: string }> }) {
  return (
    <div className="flex items-center gap-3 mb-4 mt-10 first:mt-0">
      <Icon size={18} className="text-matrix" />
      <h2 className="font-pixel text-2xl text-white tracking-wider">/// {title}</h2>
      <div className="flex-1 border-b border-white/10" />
    </div>
  );
}

function ProgressBar({ value, max, label, color = 'bg-matrix' }: { value: number; max: number; label: string; color?: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-gray-500 w-20 uppercase font-bold tracking-wider">{label}</span>
      <div className="flex-1 h-2 bg-white/5 border border-white/10 relative">
        <motion.div
          className={`h-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs font-mono text-gray-400 w-12 text-right">{pct.toFixed(0)}%</span>
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [vocab, setVocab] = useState<VocabData | null>(null);
  const [sessions, setSessions] = useState<SessionData | null>(null);
  const [isReachable, setIsReachable] = useState(false);
  const [latency, setLatency] = useState(0);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchAll = useCallback(async () => {
    setIsRefreshing(true);
    const start = performance.now();

    try {
      const [hRes, aRes, vRes, sRes] = await Promise.allSettled([
        fetch(`${API}/health`).then(r => r.json()),
        fetch(`${API}/api/analytics`).then(r => r.json()),
        fetch(`${API}/api/vocabulary`).then(r => r.json()),
        fetch(`${API}/api/sessions`).then(r => r.json()),
      ]);

      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (aRes.status === 'fulfilled') setAnalytics(aRes.value);
      if (vRes.status === 'fulfilled') setVocab(vRes.value);
      if (sRes.status === 'fulfilled') setSessions(sRes.value);

      setIsReachable(hRes.status === 'fulfilled');
      setLatency(Math.round(performance.now() - start));
      setLastRefresh(new Date());
    } catch {
      setIsReachable(false);
    }
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    fetchAll();
    const timer = setInterval(fetchAll, 8000);
    return () => clearInterval(timer);
  }, [fetchAll]);

  const handleClearCache = async () => {
    try {
      await fetch(`${API}/api/cache`, { method: 'DELETE' });
      fetchAll();
    } catch { /* ignore */ }
  };

  const cacheStats = health?.services.cache || analytics?.cache;
  const totalOps = (analytics?.total_translations || 0) + (analytics?.total_sign_conversions || 0);

  return (
    <div className="bg-pixel-grid min-h-screen p-4 md:p-8 font-mono">
      {/* ── Header ────────────────────────────────────────── */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 border-b-2 border-white/20 pb-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-4">
          <Link href="/">
            <motion.div
              className="w-10 h-10 bg-white/10 border border-white/20 flex items-center justify-center hover:bg-matrix hover:border-black transition-colors cursor-pointer"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <ArrowLeft size={18} />
            </motion.div>
          </Link>
          <div>
            <h1 className="font-pixel text-3xl tracking-widest text-white uppercase">
              SYSTEM_DASHBOARD
            </h1>
            <div className="flex items-center gap-3 mt-1">
              <motion.div
                className={`w-2.5 h-2.5 border border-white ${isReachable ? 'bg-matrix' : 'bg-red-500'}`}
                animate={isReachable ? { opacity: [1, 0.3, 1] } : {}}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
              <span className="text-xs text-gray-400 font-mono">
                {isReachable ? `BACKEND ONLINE • ${latency}ms` : 'BACKEND OFFLINE'}
              </span>
              {lastRefresh && (
                <span className="text-[10px] text-gray-600 font-mono">
                  LAST: {lastRefresh.toLocaleTimeString()}
                </span>
              )}
            </div>
          </div>
        </div>

        <motion.button
          onClick={fetchAll}
          disabled={isRefreshing}
          className="border border-white/30 px-4 py-2 text-xs font-bold uppercase flex items-center gap-2 hover:bg-white hover:text-black transition-colors disabled:opacity-50 cursor-pointer"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          <motion.div animate={isRefreshing ? { rotate: 360 } : {}} transition={{ duration: 0.5, repeat: isRefreshing ? Infinity : 0, ease: 'linear' }}>
            <RefreshCw size={14} />
          </motion.div>
          {isRefreshing ? 'REFRESHING...' : 'REFRESH'}
        </motion.button>
      </header>

      <div className="max-w-7xl mx-auto">
        {!isReachable ? (
          /* ── OFFLINE STATE ── */
          <motion.div
            className="text-center py-16 border border-white/10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <WifiOff size={48} className="mx-auto mb-4 text-red-500/60" />
            <p className="font-pixel text-2xl text-red-400">BACKEND UNREACHABLE</p>

            {typeof window !== 'undefined' && !window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1') ? (
              /* ── Deployed (Vercel / production) ── */
              <div className="mt-4 max-w-lg mx-auto">
                <p className="font-mono text-xs text-gray-400 leading-relaxed">
                  This dashboard monitors a <span className="text-matrix">local backend</span> running on your machine.
                  It is not available on cloud deployments.
                </p>
                <div className="border border-white/10 bg-black/50 p-4 mt-4 text-left">
                  <p className="text-[10px] uppercase text-gray-500 font-bold tracking-wider mb-2">TO USE THIS DASHBOARD:</p>
                  <ol className="text-xs text-gray-400 font-mono space-y-2 list-decimal list-inside">
                    <li>Clone the repo and run the backend locally</li>
                    <li>Start: <code className="text-matrix">uvicorn app.main:app --reload</code></li>
                    <li>Open <code className="text-matrix">http://localhost:3000/dashboard</code></li>
                  </ol>
                </div>
                <p className="text-[10px] text-gray-600 font-mono mt-3">
                  TARGETING: <code className="text-gray-500">{API}</code>
                </p>
              </div>
            ) : (
              /* ── Local development ── */
              <div className="mt-4 max-w-lg mx-auto">
                <p className="font-mono text-xs text-gray-500">
                  Start the backend: <code className="text-matrix">uvicorn app.main:app --reload</code>
                </p>
                <p className="text-[10px] text-gray-600 font-mono mt-2">
                  TARGETING: <code className="text-gray-500">{API}</code>
                </p>
              </div>
            )}
          </motion.div>
        ) : (
          <>
            {/* ═══ HEALTH OVERVIEW ═══ */}
            <SectionHeader title="SYSTEM_HEALTH" icon={Activity} />
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <StatCard icon={Wifi} label="Status" value={health?.status?.toUpperCase() || '—'} sub={`v${health?.version || '?'}`} delay={0} />
              <StatCard icon={Clock} label="Uptime" value={health?.uptime || '—'} sub={health?.config.environment?.toUpperCase()} delay={0.05} />
              <StatCard icon={Cpu} label="Grammar" value={health?.services.grammar_engine?.includes('openai') ? 'GPT-4o' : 'RULES'} sub={health?.services.grammar_engine || '—'} delay={0.1} color={health?.services.grammar_engine?.includes('openai') ? 'text-cyan-400' : 'text-white'} />
              <StatCard icon={Cpu} label="Translation" value={health?.services.translation_engine?.includes('openai') ? 'LLM' : 'VOCAB'} sub={health?.services.translation_engine || '—'} delay={0.15} color={health?.services.translation_engine?.includes('openai') ? 'text-cyan-400' : 'text-white'} />
              <StatCard icon={Users} label="Connections" value={health?.services.active_connections || 0} sub={`${health?.services.active_sessions || 0} sessions`} delay={0.2} />
              <StatCard icon={Zap} label="Latency" value={`${latency}ms`} sub={latency < 50 ? 'OPTIMAL' : latency < 150 ? 'MODERATE' : 'HIGH'} delay={0.25} color={latency < 50 ? 'text-matrix' : latency < 150 ? 'text-yellow-400' : 'text-red-400'} />
            </div>

            {/* ═══ ANALYTICS ═══ */}
            <SectionHeader title="ANALYTICS" icon={BarChart3} />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard icon={TrendingUp} label="Translations" value={analytics?.total_translations || 0} sub="Sign → Speech" delay={0.05} />
              <StatCard icon={TrendingUp} label="Sign Converts" value={analytics?.total_sign_conversions || 0} sub="Speech → Sign" delay={0.1} />
              <StatCard icon={Activity} label="Total Ops" value={totalOps} sub={`${analytics?.total_errors || 0} errors`} delay={0.15} />
              <StatCard icon={Zap} label="Rate Limited" value={analytics?.rate_limiter?.total_denied || 0} sub={`${analytics?.rate_limiter?.active_clients || 0} tracked clients`} delay={0.2} color="text-yellow-400" />
            </div>

            {/* Latency Breakdown */}
            {analytics?.avg_latency_ms && Object.keys(analytics.avg_latency_ms).length > 0 && (
              <motion.div
                className="mt-4 border border-white/10 p-5 bg-black/30"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <div className="text-[10px] uppercase text-gray-500 tracking-wider font-bold mb-3">AVG LATENCY BY OPERATION</div>
                <div className="space-y-3">
                  {Object.entries(analytics.avg_latency_ms).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 w-28 uppercase font-mono">{key}</span>
                      <div className="flex-1 h-3 bg-white/5 border border-white/10 relative">
                        <motion.div
                          className={`h-full ${val < 50 ? 'bg-matrix' : val < 200 ? 'bg-yellow-500' : 'bg-red-500'}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min((val / 500) * 100, 100)}%` }}
                          transition={{ duration: 0.8 }}
                        />
                      </div>
                      <span className="text-xs font-pixel text-white w-20 text-right">{val.toFixed(1)}ms</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* ═══ CACHE ═══ */}
            <SectionHeader title="TRANSLATION_CACHE" icon={Database} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Cache Stats */}
              <motion.div
                className="border border-white/10 p-5 bg-black/30"
                initial={{ opacity: 0, x: -15 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
              >
                <div className="grid grid-cols-2 gap-4 mb-5">
                  <div>
                    <div className="text-[10px] uppercase text-gray-500 font-bold tracking-wider">Grammar</div>
                    <div className="text-xl font-pixel text-matrix">{cacheStats?.grammar_entries || 0}</div>
                    <div className="text-[9px] text-gray-600 font-mono">ENTRIES</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase text-gray-500 font-bold tracking-wider">Sign</div>
                    <div className="text-xl font-pixel text-cyan-400">{cacheStats?.sign_entries || 0}</div>
                    <div className="text-[9px] text-gray-600 font-mono">ENTRIES</div>
                  </div>
                </div>

                <div className="space-y-2">
                  <ProgressBar
                    label="Hit Rate"
                    value={cacheStats?.hit_rate_pct || 0}
                    max={100}
                    color={
                      (cacheStats?.hit_rate_pct || 0) > 70 ? 'bg-matrix' :
                      (cacheStats?.hit_rate_pct || 0) > 30 ? 'bg-yellow-500' : 'bg-red-500'
                    }
                  />
                  <ProgressBar
                    label="Capacity"
                    value={cacheStats?.total_entries || 0}
                    max={(cacheStats?.max_size_per_type || 256) * 2}
                  />
                </div>
              </motion.div>

              {/* Cache Actions */}
              <motion.div
                className="border border-white/10 p-5 bg-black/30 flex flex-col justify-between"
                initial={{ opacity: 0, x: 15 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.25 }}
              >
                <div>
                  <div className="grid grid-cols-2 gap-4 mb-5">
                    <div>
                      <div className="text-[10px] uppercase text-gray-500 font-bold tracking-wider">Hits</div>
                      <div className="text-xl font-pixel text-matrix">{cacheStats?.hits || 0}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase text-gray-500 font-bold tracking-wider">Misses</div>
                      <div className="text-xl font-pixel text-red-400">{cacheStats?.misses || 0}</div>
                    </div>
                  </div>
                  <div className="text-[10px] text-gray-600 font-mono">
                    TTL: {cacheStats?.ttl_seconds || 3600}s • MAX: {cacheStats?.max_size_per_type || 256}/type
                  </div>
                </div>

                <motion.button
                  onClick={handleClearCache}
                  className="mt-4 w-full border border-red-500/30 text-red-400 px-4 py-2 text-xs font-bold uppercase flex items-center justify-center gap-2 hover:bg-red-500/10 transition-colors cursor-pointer"
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Trash2 size={14} />
                  CLEAR CACHE
                </motion.button>
              </motion.div>
            </div>

            {/* ═══ SESSIONS ═══ */}
            <SectionHeader title="ACTIVE_SESSIONS" icon={Users} />
            <AnimatePresence>
              {sessions?.sessions && sessions.sessions.length > 0 ? (
                <div className="space-y-2">
                  {sessions.sessions.map((s, i) => (
                    <motion.div
                      key={s.session_id}
                      className="border border-white/10 p-4 bg-black/30 flex flex-col md:flex-row md:items-center gap-3 md:gap-6 hover:border-matrix/30 transition-colors"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-matrix rounded-full animate-pulse" />
                        <span className="font-mono text-xs text-matrix">{s.session_id}</span>
                      </div>
                      <span className="text-[10px] text-gray-400 font-mono uppercase border border-white/10 px-2 py-0.5">{s.mode}</span>
                      <span className="text-[10px] text-gray-500 font-mono">{s.duration}</span>
                      <div className="flex gap-4 ml-auto text-[10px] font-mono text-gray-500">
                        <span>G:{s.gestures}</span>
                        <span>S:{s.speeches}</span>
                        <span>M:{s.manual_inputs}</span>
                        <span className={s.errors > 0 ? 'text-red-400' : ''}>E:{s.errors}</span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <motion.div
                  className="border border-white/10 p-8 text-center text-gray-600"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <Users size={32} className="mx-auto mb-2 opacity-30" />
                  <p className="font-pixel text-lg">NO ACTIVE SESSIONS</p>
                  <p className="text-xs font-mono mt-1">Connect to ws://localhost:8000/ws to start a session</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* ═══ VOCABULARY ═══ */}
            <SectionHeader title="VOCABULARY_MAP" icon={BookOpen} />
            <motion.div
              className="border border-white/10 p-5 bg-black/30"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <div className="flex items-center gap-6 mb-4">
                <div>
                  <div className="text-[10px] text-gray-500 uppercase font-bold tracking-wider">Total Words</div>
                  <div className="text-xl font-pixel text-matrix">{vocab?.total_words || 0}</div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500 uppercase font-bold tracking-wider">Unique Signs</div>
                  <div className="text-xl font-pixel text-cyan-400">{vocab?.total_signs || 0}</div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500 uppercase font-bold tracking-wider">Skip Words</div>
                  <div className="text-xl font-pixel text-gray-400">{vocab?.skip_words?.length || 0}</div>
                </div>
              </div>

              {vocab?.vocabulary && (
                <div className="max-h-60 overflow-y-auto scrollbar-thin border-t border-white/10 pt-3">
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-1">
                    {Object.entries(vocab.vocabulary).sort(([a], [b]) => a.localeCompare(b)).map(([word, sign]) => (
                      <div key={word} className="flex items-center gap-2 py-0.5">
                        <span className="text-xs text-gray-400 font-mono truncate">{word}</span>
                        <span className="text-[10px] text-gray-700">→</span>
                        <span className="text-xs text-matrix font-mono truncate">{sign}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          </>
        )}
      </div>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto mt-16 border-t border-white/10 pt-6 pb-4 flex justify-between items-center text-xs text-gray-600">
        <Link href="/" className="text-gray-400 hover:text-matrix transition-colors font-mono flex items-center gap-2">
          <Terminal size={14} />
          ← BACK TO TERMINAL
        </Link>
        <span className="font-mono text-gray-700">SHIA SYSTEM DASHBOARD</span>
      </footer>
    </div>
  );
}
