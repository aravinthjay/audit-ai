"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getAgentAccuracy,
  getAnalyticsKpis,
  getAnalyticsTrend,
  getLlmByModel,
  getLlmByProvider,
  getLlmCostTrends,
  getLlmRecentCalls,
  getLlmSummary,
  getRequestAnalytics,
} from "@/services/analytics.service";
import type { LLMAnalyticsFilters } from "@/types/domain";

// Poll cost/LLM telemetry so the panel updates live while a case is running.
const LIVE_REFETCH_MS = 5_000;

export function useAnalyticsTrend() {
  return useQuery({
    queryKey: ["analytics-trend"],
    queryFn: getAnalyticsTrend,
  });
}

export function useAgentAccuracy() {
  return useQuery({
    queryKey: ["agent-accuracy"],
    queryFn: getAgentAccuracy,
  });
}

export function useAnalyticsKpis() {
  return useQuery({
    queryKey: ["analytics-kpis"],
    queryFn: getAnalyticsKpis,
  });
}

export function useRequestAnalytics() {
  return useQuery({
    queryKey: ["request-analytics"],
    queryFn: getRequestAnalytics,
  });
}

export function useLlmSummary(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-summary", filters],
    queryFn: () => getLlmSummary(filters),
    refetchInterval: LIVE_REFETCH_MS,
    staleTime: 0,
  });
}

export function useLlmByProvider(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-by-provider", filters],
    queryFn: () => getLlmByProvider(filters),
    refetchInterval: LIVE_REFETCH_MS,
    staleTime: 0,
  });
}

export function useLlmByModel(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-by-model", filters],
    queryFn: () => getLlmByModel(filters),
    refetchInterval: LIVE_REFETCH_MS,
    staleTime: 0,
  });
}

export function useLlmRecentCalls(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-recent", filters],
    queryFn: () => getLlmRecentCalls(filters),
    refetchInterval: LIVE_REFETCH_MS,
    staleTime: 0,
  });
}

export function useLlmCostTrends(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-cost-trends", filters],
    queryFn: () => getLlmCostTrends(filters),
    refetchInterval: LIVE_REFETCH_MS,
    staleTime: 0,
  });
}
