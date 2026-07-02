import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LLMAnalyticsPanel } from "@/components/analytics/llm-analytics-panel";
import type { LLMAnalyticsSummary } from "@/types/domain";

const summary: LLMAnalyticsSummary = {
  totalTokens: 12500,
  promptTokens: 9000,
  completionTokens: 3500,
  totalEstimatedCostUsd: 0.0425,
  totalActualCostUsd: null,
  successfulCalls: 7,
  failedCalls: 1,
  fallbackCalls: 2,
  cacheHits: 1,
  averageLatencyMs: 820,
  mostExpensiveRequestTypes: [{ requestType: "adjudication", estimatedCostUsd: 0.03 }],
};

describe("LLMAnalyticsPanel", () => {
  it("renders LLM usage cards, charts, recent calls, and filters", () => {
    const onFiltersChange = vi.fn();
    render(
      <LLMAnalyticsPanel
        filters={{}}
        onFiltersChange={onFiltersChange}
        summary={summary}
        byProvider={[
          {
            ...summary,
            providerName: "anthropic",
            calls: 4,
          },
        ]}
        byModel={[
          {
            ...summary,
            modelName: "claude-3-5-sonnet-20241022",
            calls: 4,
          },
        ]}
        trends={[
          {
            period: "2026-07-01",
            calls: 7,
            totalTokens: 12500,
            estimatedCostUsd: 0.0425,
            fallbackCalls: 2,
            averageLatencyMs: 820,
          },
        ]}
        recentCalls={[
          {
            id: "llm-call-1",
            providerName: "anthropic",
            modelName: "claude-3-5-sonnet-20241022",
            requestType: "adjudication",
            promptTokens: 1200,
            completionTokens: 420,
            totalTokens: 1620,
            estimatedCostUsd: 0.01,
            actualCostUsd: null,
            latencyMs: 860,
            success: true,
            fallbackUsed: false,
            cacheHit: false,
            modelTier: "reasoning",
          },
        ]}
      />,
    );

    expect(screen.getByText("Total tokens")).toBeInTheDocument();
    expect(screen.getByText("Cost and tokens by provider")).toBeInTheDocument();
    expect(screen.getByText("Recent LLM calls")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Provider"), { target: { value: "groq" } });
    expect(onFiltersChange).toHaveBeenCalledWith({ provider: "groq" });
  });
});
