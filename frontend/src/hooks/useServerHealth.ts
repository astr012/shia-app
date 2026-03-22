'use client';

// ============================================================
// PIPELINE LAYER 4: Server Health Polling
// Periodically fetches backend /health for live system metrics
//
// Provides: backend version, uptime, engine status, latency,
// connection count, and reachability status.
// ============================================================

import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const POLL_INTERVAL_MS = 5000;  // Poll every 5 seconds

export interface ServerHealth {
  status: string;
  version: string;
  uptime: string;
  timestamp: string;
  services: {
    grammar_engine: string;
    translation_engine: string;
    active_connections: number;
    active_sessions: number;
  };
  config: {
    app: string;
    version: string;
    environment: string;
    openai_configured: boolean;
    openai_model: string | null;
  };
}

export interface ServerHealthState {
  health: ServerHealth | null;
  isReachable: boolean;
  latencyMs: number;
  lastChecked: number;
  error: string | null;
}

interface UseServerHealthOptions {
  enabled?: boolean;
  pollInterval?: number;
}

export function useServerHealth({
  enabled = true,
  pollInterval = POLL_INTERVAL_MS,
}: UseServerHealthOptions = {}): ServerHealthState & { refetch: () => void } {
  const [health, setHealth] = useState<ServerHealth | null>(null);
  const [isReachable, setIsReachable] = useState(false);
  const [latencyMs, setLatencyMs] = useState(0);
  const [lastChecked, setLastChecked] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchHealth = useCallback(async () => {
    const start = performance.now();
    try {
      const res = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000), // 3s timeout
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data: ServerHealth = await res.json();
      const elapsed = Math.round(performance.now() - start);

      setHealth(data);
      setIsReachable(true);
      setLatencyMs(elapsed);
      setLastChecked(Date.now());
      setError(null);
    } catch (err) {
      setIsReachable(false);
      setLatencyMs(0);
      setError(err instanceof Error ? err.message : 'Unknown error');
      setLastChecked(Date.now());
    }
  }, []);

  // Start/stop polling
  useEffect(() => {
    if (!enabled) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    // Immediate first fetch
    fetchHealth();

    // Then poll
    timerRef.current = setInterval(fetchHealth, pollInterval);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [enabled, pollInterval, fetchHealth]);

  return {
    health,
    isReachable,
    latencyMs,
    lastChecked,
    error,
    refetch: fetchHealth,
  };
}
