/**
 * useChatSocket — keeps a WebSocket open to /api/ws/chat/{workshop_id}.
 *
 * Features:
 *  - Auto-reconnect with exponential backoff (1s → 2s → 4s → 8s, capped 30s).
 *  - After 3 consecutive failed reconnects, surfaces `mode === 'fallback'` so the
 *    parent can switch to polling.
 *  - Sends a ping every 25s to keep proxies from idling the connection.
 *  - Pushes incoming server payloads to the consumer via the onMessage callback.
 */
import { useEffect, useRef, useState, useCallback } from "react";

const BACKOFF_MS = [1000, 2000, 4000, 8000, 16000, 30000];
const FALLBACK_AFTER = 3;
const PING_INTERVAL_MS = 25000;

function wsUrl(workshopId) {
  const base = process.env.REACT_APP_BACKEND_URL || window.location.origin;
  return base.replace(/^http/, "ws") + `/api/ws/chat/${workshopId}`;
}

export default function useChatSocket({ workshopId, onMessage }) {
  const [status, setStatus] = useState("connecting"); // connecting | connected | reconnecting | fallback | offline
  const wsRef = useRef(null);
  const attemptsRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const pingTimerRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const closedByUserRef = useRef(false);

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    if (pingTimerRef.current) clearInterval(pingTimerRef.current);
    if (wsRef.current) {
      try { wsRef.current.close(); } catch {/* noop */}
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (closedByUserRef.current) return;
    cleanup();
    setStatus(attemptsRef.current === 0 ? "connecting" : "reconnecting");
    const ws = new WebSocket(wsUrl(workshopId));
    wsRef.current = ws;

    ws.onopen = () => {
      attemptsRef.current = 0;
      setStatus("connected");
      pingTimerRef.current = setInterval(() => {
        try { ws.send(JSON.stringify({ type: "ping" })); } catch {/* noop */}
      }, PING_INTERVAL_MS);
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        onMessageRef.current?.(data);
      } catch {/* ignore */}
    };

    ws.onclose = () => {
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (closedByUserRef.current) return;
      attemptsRef.current += 1;
      if (attemptsRef.current > FALLBACK_AFTER) {
        setStatus("fallback");
        return;
      }
      const delay = BACKOFF_MS[Math.min(attemptsRef.current - 1, BACKOFF_MS.length - 1)];
      setStatus("reconnecting");
      reconnectTimerRef.current = setTimeout(connect, delay);
    };

    ws.onerror = () => {
      try { ws.close(); } catch {/* noop */}
    };
  }, [workshopId, cleanup]);

  useEffect(() => {
    closedByUserRef.current = false;
    attemptsRef.current = 0;
    connect();
    return () => {
      closedByUserRef.current = true;
      cleanup();
    };
  }, [connect, cleanup]);

  const send = useCallback((payload) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }, []);

  return { status, send };
}
