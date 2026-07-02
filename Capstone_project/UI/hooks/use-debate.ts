"use client";

import { useQuery } from "@tanstack/react-query";
import { getDebateArguments } from "@/services/debate.service";

export function useDebateArguments(caseId?: string, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["debate", caseId ?? ""],
    queryFn: () => getDebateArguments(caseId),
    enabled: options.enabled ?? Boolean(caseId),
  });
}
