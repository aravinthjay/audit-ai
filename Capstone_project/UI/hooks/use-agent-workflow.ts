"use client";

import { useQuery } from "@tanstack/react-query";
import { getAgentHealth, getAgentWorkflow } from "@/services/agents.service";

export function useAgentWorkflow(caseId?: string) {
  return useQuery({
    queryKey: ["agent-workflow", caseId],
    queryFn: () => getAgentWorkflow(caseId),
    enabled: Boolean(caseId),
    // Poll so the workflow diagram advances live while a case runs, even if the
    // websocket is unavailable.
    refetchInterval: 5_000,
    staleTime: 0,
  });
}

export function useAgentHealth() {
  return useQuery({
    queryKey: ["agent-health"],
    queryFn: getAgentHealth,
  });
}
