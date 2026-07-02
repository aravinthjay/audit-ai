import { describe, expect, it } from "vitest";
import { getLlmByProvider, getLlmRecentCalls, getLlmSummary, getRequestAnalytics } from "@/services/analytics.service";

describe("analytics service", () => {
  it("maps request telemetry from the backend", async () => {
    const result = await getRequestAnalytics();

    expect(result.totalRequests).toBe(4);
    expect(result.avgDurationMs).toBe(42.5);
    expect(result.byStatus["200"]).toBe(4);
    expect(result.topPaths[0]).toMatchObject({ path: "/api/v1/investigations", count: 2 });
    expect(result.recent[0]).toMatchObject({
      requestId: "req-test-1",
      statusCode: 200,
    });
  });

  it("maps LLM usage analytics from the backend", async () => {
    const summary = await getLlmSummary({ provider: "anthropic" });
    const byProvider = await getLlmByProvider();
    const recent = await getLlmRecentCalls();

    expect(summary.totalTokens).toBe(12500);
    expect(summary.totalEstimatedCostUsd).toBe(0.0425);
    expect(summary.fallbackCalls).toBe(2);
    expect(byProvider[0]).toMatchObject({ providerName: "anthropic", totalTokens: 9000 });
    expect(recent[0]).toMatchObject({ providerName: "anthropic", requestType: "adjudication" });
  });
});
