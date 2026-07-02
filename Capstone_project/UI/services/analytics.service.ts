import { apiRequest } from "@/services/api";
import type {
  AgentAccuracy,
  AnalyticsKpi,
  AnalyticsPoint,
  LLMAggregate,
  LLMAnalyticsFilters,
  LLMAnalyticsSummary,
  LLMCostTrend,
  LLMRecentCall,
  RequestAnalytics,
} from "@/types/domain";

type ApiTrendPoint = { week: string; confidence: number; verifier_rate: number };
type ApiRequestAnalytics = {
  total_requests: number;
  error_rate: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  by_status: Record<string, number>;
  top_paths: Array<{ path: string; count: number }>;
  recent: Array<{
    request_id: string;
    method: string;
    path: string;
    status_code: number;
    duration_ms: number;
    created_at?: string | null;
  }>;
};
type ApiLLMSummary = {
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_estimated_cost_usd: number;
  total_actual_cost_usd?: number | null;
  successful_calls: number;
  failed_calls: number;
  fallback_calls: number;
  cache_hits: number;
  average_latency_ms: number;
  most_expensive_request_types: Array<{ request_type: string; estimated_cost_usd: number }>;
};
type ApiLLMAggregate = ApiLLMSummary & {
  provider_name?: string;
  model_name?: string;
  calls: number;
};
type ApiLLMRecentCall = {
  id: string;
  provider_name: string;
  model_name: string;
  request_type: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  actual_cost_usd?: number | null;
  latency_ms: number;
  success: boolean;
  error_message?: string | null;
  fallback_used: boolean;
  fallback_provider?: string | null;
  cache_hit: boolean;
  model_tier: string;
  routing_reason?: string | null;
  quality_guardrail?: string | null;
  user_id?: string | null;
  session_id?: string | null;
  request_id?: string | null;
  created_at?: string | null;
};
type ApiLLMCostTrend = {
  period: string;
  calls: number;
  total_tokens: number;
  estimated_cost_usd: number;
  fallback_calls: number;
  average_latency_ms: number;
};

export async function getAnalyticsTrend(): Promise<AnalyticsPoint[]> {
  const rows = await apiRequest<ApiTrendPoint[]>("/analytics/trend");
  return rows.map((row) => ({
    week: row.week,
    confidence: row.confidence,
    verifierRate: row.verifier_rate,
  }));
}

export async function getAgentAccuracy(): Promise<AgentAccuracy[]> {
  return apiRequest<AgentAccuracy[]>("/analytics/agent-accuracy");
}

export async function getAnalyticsKpis(): Promise<AnalyticsKpi[]> {
  return apiRequest<AnalyticsKpi[]>("/analytics/kpis");
}

export async function getRequestAnalytics(): Promise<RequestAnalytics> {
  const payload = await apiRequest<ApiRequestAnalytics>("/analytics/requests");
  return {
    totalRequests: payload.total_requests,
    errorRate: payload.error_rate,
    avgDurationMs: payload.avg_duration_ms,
    p95DurationMs: payload.p95_duration_ms,
    byStatus: payload.by_status,
    topPaths: payload.top_paths,
    recent: payload.recent.map((row) => ({
      requestId: row.request_id,
      method: row.method,
      path: row.path,
      statusCode: row.status_code,
      durationMs: row.duration_ms,
      createdAt: row.created_at,
    })),
  };
}

function llmQuery(filters: LLMAnalyticsFilters = {}) {
  const params = new URLSearchParams();
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  if (filters.provider) {
    params.set("provider", filters.provider);
  }
  if (filters.model) {
    params.set("model", filters.model);
  }
  if (filters.requestType) {
    params.set("request_type", filters.requestType);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

function mapLlmSummary(payload: ApiLLMSummary): LLMAnalyticsSummary {
  return {
    totalTokens: payload.total_tokens,
    promptTokens: payload.prompt_tokens,
    completionTokens: payload.completion_tokens,
    totalEstimatedCostUsd: payload.total_estimated_cost_usd,
    totalActualCostUsd: payload.total_actual_cost_usd,
    successfulCalls: payload.successful_calls,
    failedCalls: payload.failed_calls,
    fallbackCalls: payload.fallback_calls,
    cacheHits: payload.cache_hits,
    averageLatencyMs: payload.average_latency_ms,
    mostExpensiveRequestTypes: payload.most_expensive_request_types.map((item) => ({
      requestType: item.request_type,
      estimatedCostUsd: item.estimated_cost_usd,
    })),
  };
}

function mapLlmAggregate(payload: ApiLLMAggregate): LLMAggregate {
  return {
    ...mapLlmSummary(payload),
    providerName: payload.provider_name,
    modelName: payload.model_name,
    calls: payload.calls,
  };
}

function mapLlmCall(payload: ApiLLMRecentCall): LLMRecentCall {
  return {
    id: payload.id,
    providerName: payload.provider_name,
    modelName: payload.model_name,
    requestType: payload.request_type,
    promptTokens: payload.prompt_tokens,
    completionTokens: payload.completion_tokens,
    totalTokens: payload.total_tokens,
    estimatedCostUsd: payload.estimated_cost_usd,
    actualCostUsd: payload.actual_cost_usd,
    latencyMs: payload.latency_ms,
    success: payload.success,
    errorMessage: payload.error_message,
    fallbackUsed: payload.fallback_used,
    fallbackProvider: payload.fallback_provider,
    cacheHit: payload.cache_hit,
    modelTier: payload.model_tier,
    routingReason: payload.routing_reason,
    qualityGuardrail: payload.quality_guardrail,
    userId: payload.user_id,
    sessionId: payload.session_id,
    requestId: payload.request_id,
    createdAt: payload.created_at,
  };
}

export async function getLlmSummary(filters?: LLMAnalyticsFilters): Promise<LLMAnalyticsSummary> {
  return mapLlmSummary(await apiRequest<ApiLLMSummary>(`/analytics/llm/summary${llmQuery(filters)}`));
}

export async function getLlmByProvider(filters?: LLMAnalyticsFilters): Promise<LLMAggregate[]> {
  const rows = await apiRequest<ApiLLMAggregate[]>(`/analytics/llm/by-provider${llmQuery(filters)}`);
  return rows.map(mapLlmAggregate);
}

export async function getLlmByModel(filters?: LLMAnalyticsFilters): Promise<LLMAggregate[]> {
  const rows = await apiRequest<ApiLLMAggregate[]>(`/analytics/llm/by-model${llmQuery(filters)}`);
  return rows.map(mapLlmAggregate);
}

export async function getLlmRecentCalls(filters?: LLMAnalyticsFilters): Promise<LLMRecentCall[]> {
  const rows = await apiRequest<ApiLLMRecentCall[]>(`/analytics/llm/recent-calls${llmQuery(filters)}`);
  return rows.map(mapLlmCall);
}

export async function getLlmCostTrends(filters?: LLMAnalyticsFilters): Promise<LLMCostTrend[]> {
  const rows = await apiRequest<ApiLLMCostTrend[]>(`/analytics/llm/cost-trends${llmQuery(filters)}`);
  return rows.map((row) => ({
    period: row.period,
    calls: row.calls,
    totalTokens: row.total_tokens,
    estimatedCostUsd: row.estimated_cost_usd,
    fallbackCalls: row.fallback_calls,
    averageLatencyMs: row.average_latency_ms,
  }));
}
