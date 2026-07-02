"use client";

import { useQuery } from "@tanstack/react-query";
import { getVerificationClaims } from "@/services/verification.service";

export function useVerificationClaims(caseId?: string, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["verification", caseId ?? ""],
    queryFn: () => getVerificationClaims(caseId),
    enabled: options.enabled ?? Boolean(caseId),
  });
}
