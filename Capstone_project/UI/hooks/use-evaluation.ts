"use client";

import { useQuery } from "@tanstack/react-query";
import { getCaseEvaluation, getEvaluationSummary } from "@/services/evaluation.service";

export function useEvaluationSummary() {
  return useQuery({
    queryKey: ["evaluation-summary"],
    queryFn: getEvaluationSummary,
  });
}

export function useCaseEvaluation(caseId: string | undefined) {
  return useQuery({
    queryKey: ["evaluation-case", caseId],
    queryFn: () => getCaseEvaluation(caseId as string),
    enabled: Boolean(caseId),
    // Refresh the per-case RAGAS scores as the case progresses.
    refetchInterval: 8_000,
    staleTime: 0,
  });
}
