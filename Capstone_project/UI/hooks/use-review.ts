"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getReviewHistory, submitReviewDecision } from "@/services/reviews.service";

export function useReviewHistory(caseId?: string, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["review-history", caseId ?? ""],
    queryFn: () => getReviewHistory(caseId),
    enabled: options.enabled ?? Boolean(caseId),
  });
}

export function useSubmitReviewDecision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: submitReviewDecision,
    onSuccess: async (_response, input) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["investigation", input.caseId] }),
        queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
        queryClient.invalidateQueries({ queryKey: ["review-history", input.caseId] }),
        queryClient.invalidateQueries({ queryKey: ["audit-events", input.caseId] }),
      ]);
    },
  });
}
