// ============================================================
// SignAI_OS — Utility Functions
// ============================================================

import { LogEntry, LogSource } from './types';

/**
 * Generate a unique ID for log entries
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Create a new log entry
 */
export function createLogEntry(source: LogSource, text: string, confidence?: number): LogEntry {
  return {
    id: generateId(),
    source,
    text,
    timestamp: new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
    confidence,
  };
}

/**
 * Format confidence percentage
 */
export function formatConfidence(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Clamp a number between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
