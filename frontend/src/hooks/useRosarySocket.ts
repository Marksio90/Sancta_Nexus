"use client";

import { useEffect, useRef, useCallback, useState } from "react";

// ── Protokół wiadomości ────────────────────────────────────────────────────

export type WsMessageType =
  | "state"
  | "joined"
  | "left"
  | "decade"
  | "pong"
  | "error";

export interface WsState {
  type: "state";
  participants: number;
  decades_completed: number[];
  mystery_type: string;
}

export interface WsJoined {
  type: "joined";
  user_id: string;
  participants: number;
}

export interface WsLeft {
  type: "left";
  user_id: string;
  participants: number;
}

export interface WsDecade {
  type: "decade";
  decade: number;
  user_id: string;
  participants: number;
}

export interface WsError {
  type: "error";
  message: string;
}

export type WsMessage = WsState | WsJoined | WsLeft | WsDecade | WsError | { type: "pong" };

// ── Hook ───────────────────────────────────────────────────────────────────

export interface RosarySocketState {
  connected: boolean;
  participants: number;
  decadesCompleted: number[];
  lastDecadeBy: string | null;
  mysteryType: string | null;
  error: string | null;
}

export interface RosarySocketActions {
  sendDecade: (decade: number) => void;
  disconnect: () => void;
}

const WS_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
        .replace(/^http/, "ws")
    : "ws://localhost:8000";

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000]; // max 4 tentatyw

export function useRosarySocket(
  sessionId: string | null
): RosarySocketState & RosarySocketActions {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const isMounted = useRef(true);

  const [state, setState] = useState<RosarySocketState>({
    connected: false,
    participants: 0,
    decadesCompleted: [],
    lastDecadeBy: null,
    mysteryType: null,
    error: null,
  });

  const connect = useCallback(() => {
    if (!sessionId || !isMounted.current) return;

    const token = typeof window !== "undefined"
      ? localStorage.getItem("token")
      : null;

    if (!token) {
      setState((s) => ({ ...s, error: "Brak tokenu — zaloguj się." }));
      return;
    }

    const url = `${WS_BASE}/ws/rosary/${sessionId}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttempt.current = 0;
      setState((s) => ({ ...s, connected: true, error: null }));
    };

    ws.onmessage = (event: MessageEvent) => {
      let msg: WsMessage;
      try {
        msg = JSON.parse(event.data as string) as WsMessage;
      } catch {
        return;
      }

      setState((s) => {
        switch (msg.type) {
          case "state":
            return {
              ...s,
              participants: msg.participants,
              decadesCompleted: msg.decades_completed,
              mysteryType: msg.mystery_type,
            };
          case "joined":
          case "left":
            return { ...s, participants: msg.participants };
          case "decade":
            return {
              ...s,
              participants: msg.participants,
              decadesCompleted: s.decadesCompleted.includes(msg.decade)
                ? s.decadesCompleted
                : [...s.decadesCompleted, msg.decade].sort((a, b) => a - b),
              lastDecadeBy: msg.user_id,
            };
          case "error":
            return { ...s, error: msg.message };
          default:
            return s;
        }
      });
    };

    ws.onerror = () => {
      setState((s) => ({ ...s, error: "Błąd połączenia WebSocket." }));
    };

    ws.onclose = (event) => {
      setState((s) => ({ ...s, connected: false }));

      // 4001 = unauthorized — nie próbuj ponownie
      if (event.code === 4001 || !isMounted.current) return;

      const attempt = reconnectAttempt.current;
      const delay = RECONNECT_DELAYS[Math.min(attempt, RECONNECT_DELAYS.length - 1)];
      reconnectAttempt.current += 1;

      setTimeout(() => {
        if (isMounted.current) connect();
      }, delay);
    };
  }, [sessionId]);

  useEffect(() => {
    isMounted.current = true;
    connect();

    // Ping co 30s żeby utrzymać połączenie
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "ping" }));
      }
    }, 30_000);

    return () => {
      isMounted.current = false;
      clearInterval(pingInterval);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendDecade = useCallback((decade: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "complete_decade", decade }));
    }
  }, []);

  const disconnect = useCallback(() => {
    isMounted.current = false;
    wsRef.current?.close();
  }, []);

  return { ...state, sendDecade, disconnect };
}
