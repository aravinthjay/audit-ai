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
  });
}

export function useLlmByProvider(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-by-provider", filters],
    queryFn: () => getLlmByProvider(filters),
  });
}

export function useLlmByModel(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-by-model", filters],
    queryFn: () => getLlmByModel(filters),
  });
}

export function useLlmRecentCalls(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-recent", filters],
    queryFn: () => getLlmRecentCalls(filters),
  });
}

export function useLlmCostTrends(filters: LLMAnalyticsFilters) {
  return useQuery({
    queryKey: ["llm-analytics-cost-trends", filters],
    queryFn: () => getLlmCostTrends(filters),
  });
}
