"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiWebSocketUrl } from "@/services/api";

type UseInvestigationRealtimeOptions = {
  enabled?: boolean;
  onMessage?: (message: string) => void;
};

export function messageFromRealtimeEvent(value: unknown) {
  if (!value || typeof value !== "object") {
    return null;
  }

  const event = value as Record<string, unknown>;

  if (event.type === "ack") {
    return null;
  }
  if (event.type === "agent_status") {
    return [event.agent, event.state, event.message].filter(Boolean).join(" - ");
  }
  if (event.type === "pipeline_stage") {
    return `Pipeline moved from ${String(event.from_stage)} to ${String(event.to_stage)}.`;
  }
  if (event.type === "debate_message") {
    return `${String(event.speaker)} posted debate round ${String(event.round)}.`;
  }
  if (event.type === "verification") {
    return `Evidence verification completed: ${String(event.status)}.`;
  }

  return typeof event.type === "string" ? `Realtime event: ${event.type}` : null;
}

export function useInvestigationRealtime(
  caseId?: string,
  { enabled = true, onMessage }: UseInvestigationRealtimeOptions = {},
) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || !caseId || typeof WebSocket === "undefined") {
      return undefined;
    }

    const url = apiWebSocketUrl(`/ws/investigations/${caseId}`);

    if (!url) {
      return undefined;
    }

    let socket: WebSocket | null = null;
    let closedByEffect = false;
    let reconnectAttempt = 0;
    let reconnectTimer: number | undefined;

    const refreshCaseQueries = () => {
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
        queryClient.invalidateQueries({ queryKey: ["investigation", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["evidence", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["evidence-verification", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["debate", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["verification", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["audit-events", caseId] }),
      ]);
    };

    const connect = () => {
      socket = new WebSocket(url);

      socket.onopen = () => {
        reconnectAttempt = 0;
        socket?.send("subscribe");
      };
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as unknown;
          const message = messageFromRealtimeEvent(payload);

          if (message) {
            onMessage?.(message);
            refreshCaseQueries();
          }
        } catch {
          onMessage?.(String(event.data));
          refreshCaseQueries();
        }
      };
      socket.onerror = () => {
        onMessage?.("Realtime connection interrupted; reconnecting.");
        refreshCaseQueries();
      };
      socket.onclose = () => {
        if (closedByEffect) {
          return;
        }

        refreshCaseQueries();
        const delayMs = Math.min(1000 * 2 ** reconnectAttempt, 10_000);
        reconnectAttempt += 1;
        reconnectTimer = window.setTimeout(connect, delayMs);
      };
    };

    connect();

    return () => {
      closedByEffect = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      socket?.close();
    };
  }, [caseId, enabled, onMessage, queryClient]);
}
