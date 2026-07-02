"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createInvestigation,
  createInvestigations,
  deleteAllInvestigations,
  deleteImportedInvestigations,
  executeInvestigation,
  executeInvestigations,
  getDashboardSummary,
  getInvestigations,
  getReviewQueue,
} from "@/services/cases.service";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
  });
}

export function useInvestigations(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["investigations"],
    queryFn: () => getInvestigations(),
    enabled: options.enabled ?? true,
  });
}

export function useDebatedInvestigations(options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["investigations", "with-debate"],
    queryFn: () => getInvestigations({ hasDebate: true }),
    enabled: options.enabled ?? true,
  });
}

export function useReviewQueue() {
  return useQuery({
    queryKey: ["review-queue"],
    queryFn: getReviewQueue,
  });
}

export function useCreateInvestigation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createInvestigation,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
      ]);
    },
  });
}

export function useCreateInvestigations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createInvestigations,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
      ]);
    },
  });
}

export function useDeleteImportedInvestigations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteImportedInvestigations,
    onSuccess: async (response) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
        queryClient.invalidateQueries({ queryKey: ["intake-summary"] }),
        ...response.investigation_ids.flatMap((caseId) => [
          queryClient.removeQueries({ queryKey: ["investigation", caseId] }),
          queryClient.removeQueries({ queryKey: ["evidence", caseId] }),
          queryClient.removeQueries({ queryKey: ["evidence-verification", caseId] }),
          queryClient.removeQueries({ queryKey: ["debate", caseId] }),
          queryClient.removeQueries({ queryKey: ["verification", caseId] }),
          queryClient.removeQueries({ queryKey: ["audit-events", caseId] }),
        ]),
      ]);
    },
  });
}

export function useDeleteAllInvestigations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteAllInvestigations,
    onSuccess: async () => {
      // Everything is gone, so clear the whole cache rather than surgically
      // invalidating individual case keys.
      queryClient.clear();
    },
  });
}

export function useExecuteInvestigation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: executeInvestigation,
    onSuccess: async (_response, caseId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["investigation", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["evidence", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["evidence-verification", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["debate", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["verification", caseId] }),
        queryClient.invalidateQueries({ queryKey: ["audit-events", caseId] }),
      ]);
    },
  });
}

export function useExecuteInvestigations() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: executeInvestigations,
    onSuccess: async (_response, caseIds) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
        queryClient.invalidateQueries({ queryKey: ["investigations"] }),
        queryClient.invalidateQueries({ queryKey: ["review-queue"] }),
        ...caseIds.flatMap((caseId) => [
          queryClient.invalidateQueries({ queryKey: ["investigation", caseId] }),
          queryClient.invalidateQueries({ queryKey: ["evidence", caseId] }),
          queryClient.invalidateQueries({ queryKey: ["evidence-verification", caseId] }),
          queryClient.invalidateQueries({ queryKey: ["debate", caseId] }),
          queryClient.invalidateQueries({ queryKey: ["verification", caseId] }),
          queryClient.invalidateQueries({ queryKey: ["audit-events", caseId] }),
        ]),
      ]);
    },
  });
}
