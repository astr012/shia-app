'use client';

// ============================================================
// PIPELINE LAYER 1: WebSocket Transport
// Bi-directional real-time communication between Frontend ↔ Backend
//
// FIXED: Uses refs for callbacks to prevent reconnection loops
// when onMessage handler identity changes
// ============================================================

import { useState, useRef, useCallback, useEffect } from 'react';

export type WSStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WSMessage {
  type: string;
  payload: unknown;
  timestamp: number;
}

interface UseWebSocketOptions {
  url: string;
  autoConnect?: boolean;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: WSMessage) => void;
  onStatusChange?: (status: WSStatus) => void;
}

interface UseWebSocketReturn {
  status: WSStatus;
  send: (type: string, payload: unknown) => void;
  connect: () => void;
  disconnect: () => void;
  lastMessage: WSMessage | null;
}

export function useWebSocket({
  url,
  autoConnect = false,
  reconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
  onMessage,
  onStatusChange,
}: UseWebSocketOptions): UseWebSocketReturn {
  const [status, setStatus] = useState<WSStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalClose = useRef(false);

  // Use refs for callbacks so the WebSocket doesn't reconnect
  // when the callback identity changes (e.g. mode switch)
  const onMessageRef = useRef(onMessage);
  const onStatusChangeRef = useRef(onStatusChange);
  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);
  useEffect(() => { onStatusChangeRef.current = onStatusChange; }, [onStatusChange]);

  const updateStatus = useCallback((newStatus: WSStatus) => {
    setStatus(newStatus);
    onStatusChangeRef.current?.(newStatus);
  }, []);

  const connect = useCallback(() => {
    // Don't reconnect if already connected or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    // Clean up existing connection
    if (wsRef.current) {
      intentionalClose.current = true;
      wsRef.current.close();
    }

    intentionalClose.current = false;
    updateStatus('connecting');

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[WS] Connected to', url);
        reconnectCount.current = 0;
        updateStatus('connected');
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessageRef.current?.(message);
        } catch {
          console.warn('[WS] Failed to parse message:', event.data);
        }
      };

      ws.onerror = (event) => {
        console.error('[WS] Connection Error', event);
        updateStatus('error');
      };

      ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        updateStatus('disconnected');

        // Auto-reconnect logic (only if not intentionally closed)
        if (!intentionalClose.current && reconnect && reconnectCount.current < maxReconnectAttempts) {
          reconnectCount.current += 1;
          console.log(
            `[WS] Reconnecting... attempt ${reconnectCount.current}/${maxReconnectAttempts}`
          );
          reconnectTimer.current = setTimeout(connect, reconnectInterval);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WS] Connection failed:', error);
      updateStatus('error');
    }
  }, [url, reconnect, reconnectInterval, maxReconnectAttempts, updateStatus]);

  const disconnect = useCallback(() => {
    intentionalClose.current = true;
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    reconnectCount.current = maxReconnectAttempts; // Prevent reconnect
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    updateStatus('disconnected');
  }, [maxReconnectAttempts, updateStatus]);

  const send = useCallback(
    (type: string, payload: unknown) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const message: WSMessage = {
          type,
          payload,
          timestamp: Date.now(),
        };
        wsRef.current.send(JSON.stringify(message));
      } else {
        console.warn('[WS] Cannot send — not connected. ReadyState:', wsRef.current?.readyState);
      }
    },
    []
  );

  // Auto-connect on mount if specified
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]);

  return { status, send, connect, disconnect, lastMessage };
}
