"use client";

import { BarChart3 } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";
import { LLMAnalyticsPanel } from "@/components/analytics/llm-analytics-panel";
import { ChartSkeleton } from "@/components/shared/chart-skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  useAgentAccuracy,
  useAnalyticsKpis,
  useAnalyticsTrend,
  useLlmByModel,
  useLlmByProvider,
  useLlmCostTrends,
  useLlmRecentCalls,
  useLlmSummary,
  useRequestAnalytics,
} from "@/hooks/use-analytics";
import { downloadJson } from "@/lib/download";
import type { LLMAnalyticsFilters } from "@/types/domain";

const AnalyticsCharts = dynamic(
  () => import("@/components/analytics/analytics-charts").then((m) => m.AnalyticsCharts),
  { ssr: false, loading: () => <ChartSkeleton className="h-80" /> },
);

export function AnalyticsView() {
  const [llmFilters, setLlmFilters] = useState<LLMAnalyticsFilters>({});
  const trendQuery = useAnalyticsTrend();
  const accuracyQuery = useAgentAccuracy();
  const kpiQuery = useAnalyticsKpis();
  const requestQuery = useRequestAnalytics();
  const llmSummaryQuery = useLlmSummary(llmFilters);
  const llmByProviderQuery = useLlmByProvider(llmFilters);
  const llmByModelQuery = useLlmByModel(llmFilters);
  const llmRecentQuery = useLlmRecentCalls(llmFilters);
  const llmTrendQuery = useLlmCostTrends(llmFilters);

  if (
    trendQuery.isLoading ||
    accuracyQuery.isLoading ||
    kpiQuery.isLoading ||
    requestQuery.isLoading ||
    llmSummaryQuery.isLoading ||
    llmByProviderQuery.isLoading ||
    llmByModelQuery.isLoading ||
    llmRecentQuery.isLoading ||
    llmTrendQuery.isLoading
  ) {
    return <LoadingState label="Loading analytics" />;
  }

  if (
    trendQuery.error ||
    accuracyQuery.error ||
    kpiQuery.error ||
    requestQuery.error ||
    llmSummaryQuery.error ||
    llmByProviderQuery.error ||
    llmByModelQuery.error ||
    llmRecentQuery.error ||
    llmTrendQuery.error
  ) {
    return (
      <ErrorState
        onRetry={() =>
          void Promise.all([
            trendQuery.refetch(),
            accuracyQuery.refetch(),
            kpiQuery.refetch(),
            requestQuery.refetch(),
            llmSummaryQuery.refetch(),
            llmByProviderQuery.refetch(),
            llmByModelQuery.refetch(),
            llmRecentQuery.refetch(),
            llmTrendQuery.refetch(),
          ])
        }
      />
    );
  }

  const trend = trendQuery.data ?? [];
  const accuracy = accuracyQuery.data ?? [];
  const kpis = kpiQuery.data ?? [];
  const requestAnalytics = requestQuery.data;
  const llmSummary = llmSummaryQuery.data;
  const llmByProvider = llmByProviderQuery.data ?? [];
  const llmByModel = llmByModelQuery.data ?? [];
  const llmRecent = llmRecentQuery.data ?? [];
  const llmTrends = llmTrendQuery.data ?? [];
  const latestConfidence = trend.at(-1)?.confidence ?? 0;
  const latestVerifierRate = trend.at(-1)?.verifierRate ?? 0;
  const hasRequestAnalytics = Boolean(requestAnalytics && requestAnalytics.totalRequests > 0);
  const hasLlmAnalytics = Boolean(llmSummary);
  const hasAnalytics = trend.length > 0 || accuracy.length > 0 || kpis.length > 0 || hasRequestAnalytics || hasLlmAnalytics;

  return (
    <div className="space-y-6">
      <PageHeader
        icon={BarChart3}
        eyebrow="Analytics"
        title="How the AI is doing"
        description="See how accurate the AI has been, how often people had to step in, and how workload and confidence are trending over time."
        actions={
          <Button
            variant="secondary"
            disabled={!hasAnalytics}
            onClick={() =>
              downloadJson("analytics-dashboard", { kpis, trend, accuracy, llmSummary })
            }
          >
            <BarChart3 className="h-4 w-4" aria-hidden="true" />
            Export dashboard
          </Button>
        }
      />

      {hasAnalytics ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {kpis.map((metric) => (
              <Card key={metric.label}>
                <CardContent className="p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">{metric.label}</p>
                  <p className="mt-2 font-mono text-2xl text-foreground">{metric.value}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{metric.helper}</p>
                </CardContent>
              </Card>
            ))}
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Latest confidence</p>
                <p className="mt-2 font-mono text-2xl text-foreground">{Math.round(latestConfidence * 100)}%</p>
                <p className="mt-1 text-xs text-muted-foreground">Verifier {Math.round(latestVerifierRate * 100)}%</p>
              </CardContent>
            </Card>
          </section>

          {requestAnalytics ? (
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">API requests</p>
                  <p className="mt-2 font-mono text-2xl text-foreground">
                    {requestAnalytics.totalRequests.toLocaleString()}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">last logged sample</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Error rate</p>
                  <p className="mt-2 font-mono text-2xl text-foreground">
                    {Math.round(requestAnalytics.errorRate * 100)}%
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">5xx responses</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Avg latency</p>
                  <p className="mt-2 font-mono text-2xl text-foreground">
                    {Math.round(requestAnalytics.avgDurationMs)}ms
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">request duration</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">P95 latency</p>
                  <p className="mt-2 font-mono text-2xl text-foreground">
                    {Math.round(requestAnalytics.p95DurationMs)}ms
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {requestAnalytics.topPaths[0]?.path ?? "no path data"}
                  </p>
                </CardContent>
              </Card>
            </section>
          ) : null}

          {llmSummary ? (
            <LLMAnalyticsPanel
              filters={llmFilters}
              onFiltersChange={setLlmFilters}
              summary={llmSummary}
              byProvider={llmByProvider}
              byModel={llmByModel}
              trends={llmTrends}
              recentCalls={llmRecent}
            />
          ) : null}

          <AnalyticsCharts trend={trend} accuracy={accuracy} />
        </>
      ) : (
        <EmptyState
          title="No analytics data"
          description="Analytics will appear after the backend exposes evaluation or telemetry records."
          icon={BarChart3}
        />
      )}
    </div>
  );
}
