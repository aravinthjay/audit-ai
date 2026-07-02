"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getEvidenceVerification,
  verifyEvidence,
  type EvidenceVerificationRequest,
} from "@/services/evidence-verification.service";

export function useEvidenceVerification(
  caseId?: string,
  options: { enabled?: boolean } = {},
) {
  return useQuery({
    queryKey: ["evidence-verification", caseId ?? ""],
    queryFn: () => getEvidenceVerification(caseId),
    enabled: options.enabled ?? Boolean(caseId),
  });
}

export function useVerifyEvidence(caseId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input?: EvidenceVerificationRequest) => {
      if (!caseId) {
        throw new Error("No claim is selected for evidence verification.");
      }
      return verifyEvidence(caseId, input);
    },
    onSuccess: async () => {
      if (!caseId) {
        return;
      }

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["evidence-verification", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["investigation", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
        queryClient.invalidateQueries({ queryKey: ["audit-events", caseId] }),
      ]);
    },
  });
}
