"use client";

import { useInvestigations } from "@/hooks/use-cases";

export function useActiveInvestigationId(explicitCaseId?: string) {
  const investigationsQuery = useInvestigations({ enabled: !explicitCaseId });
  const resolvedCaseId = explicitCaseId ?? investigationsQuery.data?.[0]?.id;

  return {
    caseId: resolvedCaseId,
    error: explicitCaseId ? null : investigationsQuery.error,
    isLoading: explicitCaseId ? false : investigationsQuery.isLoading,
    refetch: investigationsQuery.refetch,
  };
}
