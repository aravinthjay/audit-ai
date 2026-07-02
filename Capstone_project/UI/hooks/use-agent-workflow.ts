"use client";

import { useQuery } from "@tanstack/react-query";
import { getAgentHealth, getAgentWorkflow } from "@/services/agents.service";

export function useAgentWorkflow(caseId?: string) {
  return useQuery({
    queryKey: ["agent-workflow", caseId],
    queryFn: () => getAgentWorkflow(caseId),
    enabled: Boolean(caseId),
  });
}

export function useAgentHealth() {
  return useQuery({
    queryKey: ["agent-health"],
    queryFn: getAgentHealth,
  });
}
