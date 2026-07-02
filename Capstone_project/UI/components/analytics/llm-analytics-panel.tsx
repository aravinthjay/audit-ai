"use client";

import { Activity, Clock, Coins, RotateCcw, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type {
  LLMAggregate,
  LLMAnalyticsFilters,
  LLMAnalyticsSummary,
  LLMCostTrend,
  LLMRecentCall,
} from "@/types/domain";

type LLMAnalyticsPanelProps = {
  filters: LLMAnalyticsFilters;
  onFiltersChange: (filters: LLMAnalyticsFilters) => void;
  summary: LLMAnalyticsSummary;
  byProvider: LLMAggregate[];
  byModel: LLMAggregate[];
  trends: LLMCostTrend[];
  recentCalls: LLMRecentCall[];
};

function compact(value: number) {
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

function money(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 4 }).format(value);
}

function updateFilter(filters: LLMAnalyticsFilters, key: keyof LLMAnalyticsFilters, value: string) {
  return { ...filters, [key]: value || undefined };
}

function BarRow({ label, value, max, helper }: { label: string; value: number; max: number; helper: string }) {
  const percent = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="truncate font-medium text-foreground">{label}</span>
        <span className="shrink-0 text-muted-foreground">{helper}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-gradient-to-r from-primary to-info transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

export function LLMAnalyticsPanel({
  filters,
  onFiltersChange,
  summary,
  byProvider,
  byModel,
  trends,
  recentCalls,
}: LLMAnalyticsPanelProps) {
  const maxProviderCost = Math.max(0, ...byProvider.map((row) => row.totalEstimatedCostUsd));
  const maxProviderTokens = Math.max(0, ...byProvider.map((row) => row.totalTokens));
  const maxTrendCost = Math.max(0, ...trends.map((row) => row.estimatedCostUsd));

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4 shadow-card md:flex-row md:items-end">
        <div className="grid flex-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <label className="text-xs font-medium text-muted-foreground">
            Date from
            <Input
              className="mt-1"
              type="date"
              value={filters.dateFrom ?? ""}
              onChange={(event) => onFiltersChange(updateFilter(filters, "dateFrom", event.target.value))}
            />
          </label>
          <label className="text-xs font-medium text-muted-foreground">
            Date to
            <Input
              className="mt-1"
              type="date"
              value={filters.dateTo ?? ""}
              onChange={(event) => onFiltersChange(updateFilter(filters, "dateTo", event.target.value))}
            />
          </label>
          <label className="text-xs font-medium text-muted-foreground">
            Provider
            <select
              className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
              value={filters.provider ?? ""}
              onChange={(event) => onFiltersChange(updateFilter(filters, "provider", event.target.value))}
            >
              <option value="">All</option>
              <option value="anthropic">Claude</option>
              <option value="groq">Groq</option>
              <option value="openai">OpenAI</option>
            </select>
          </label>
          <label className="text-xs font-medium text-muted-foreground">
            Model
            <Input
              className="mt-1"
              placeholder="Any model"
              value={filters.model ?? ""}
              onChange={(event) => onFiltersChange(updateFilter(filters, "model", event.target.value))}
            />
          </label>
          <label className="text-xs font-medium text-muted-foreground">
            Request type
            <Input
              className="mt-1"
              placeholder="Any type"
              value={filters.requestType ?? ""}
              onChange={(event) => onFiltersChange(updateFilter(filters, "requestType", event.target.value))}
            />
          </label>
        </div>
        <Button variant="secondary" type="button" onClick={() => onFiltersChange({})}>
          Clear filters
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Total tokens</p>
              <Zap className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <p className="mt-2 font-mono text-2xl text-foreground">{compact(summary.totalTokens)}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {compact(summary.promptTokens)} in / {compact(summary.completionTokens)} out
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Estimated cost</p>
              <Coins className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <p className="mt-2 font-mono text-2xl text-foreground">{money(summary.totalEstimatedCostUsd)}</p>
            <p className="mt-1 text-xs text-muted-foreground">pricing config estimate</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Fallback calls</p>
              <RotateCcw className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <p className="mt-2 font-mono text-2xl text-foreground">{summary.fallbackCalls}</p>
            <p className="mt-1 text-xs text-muted-foreground">{summary.cacheHits} cache hit(s)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Avg latency</p>
              <Clock className="h-4 w-4 text-primary" aria-hidden="true" />
            </div>
            <p className="mt-2 font-mono text-2xl text-foreground">{Math.round(summary.averageLatencyMs)}ms</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {summary.successfulCalls} ok / {summary.failedCalls} failed
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Cost and tokens by provider</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {byProvider.length ? (
              byProvider.map((row) => (
                <div key={row.providerName} className="space-y-3">
                  <BarRow
                    label={row.providerName ?? "unknown"}
                    value={row.totalEstimatedCostUsd}
                    max={maxProviderCost}
                    helper={`${money(row.totalEstimatedCostUsd)} cost`}
                  />
                  <BarRow
                    label={`${row.providerName ?? "unknown"} tokens`}
                    value={row.totalTokens}
                    max={maxProviderTokens}
                    helper={`${compact(row.totalTokens)} tokens`}
                  />
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No provider usage in this filter range.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cost trend</CardTitle>
          </CardHeader>
          <CardContent>
            {trends.length ? (
              <div className="flex h-56 items-end gap-2">
                {trends.slice(-14).map((row) => {
                  const height = maxTrendCost > 0 ? Math.max(8, Math.round((row.estimatedCostUsd / maxTrendCost) * 100)) : 8;
                  return (
                    <div key={row.period} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                      <div
                        className="w-full rounded-t-md bg-gradient-to-t from-primary to-info transition-all"
                        style={{ height: `${height}%` }}
                        title={`${row.period}: ${money(row.estimatedCostUsd)}`}
                      />
                      <span className="max-w-full truncate text-[10px] text-muted-foreground">{row.period.slice(5)}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex h-56 items-center justify-center rounded-md border border-dashed border-border text-sm text-muted-foreground">
                No cost trend data yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.4fr]">
        <Card>
          <CardHeader>
            <CardTitle>Cost by model</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {byModel.slice(0, 8).map((row) => (
              <BarRow
                key={row.modelName}
                label={row.modelName ?? "unknown"}
                value={row.totalEstimatedCostUsd}
                max={Math.max(0, ...byModel.map((item) => item.totalEstimatedCostUsd))}
                helper={`${money(row.totalEstimatedCostUsd)} / ${row.calls} calls`}
              />
            ))}
            {!byModel.length ? <p className="text-sm text-muted-foreground">No model usage yet.</p> : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent LLM calls</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.08em] text-muted-foreground">
                <tr>
                  <th className="py-2 pr-3 font-medium">Provider</th>
                  <th className="py-2 pr-3 font-medium">Model</th>
                  <th className="py-2 pr-3 font-medium">Type</th>
                  <th className="py-2 pr-3 font-medium">Tokens</th>
                  <th className="py-2 pr-3 font-medium">Cost</th>
                  <th className="py-2 pr-3 font-medium">Latency</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {recentCalls.slice(0, 12).map((call) => (
                  <tr key={call.id} className="transition-colors hover:bg-muted/50">
                    <td className="py-2 pr-3 text-foreground">{call.providerName}</td>
                    <td className="max-w-48 truncate py-2 pr-3 text-muted-foreground">{call.modelName}</td>
                    <td className="py-2 pr-3 text-muted-foreground">{call.requestType}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-foreground">{compact(call.totalTokens)}</td>
                    <td className="py-2 pr-3 font-mono text-xs text-foreground">{money(call.estimatedCostUsd)}</td>
                    <td className="py-2 pr-3 text-muted-foreground">{Math.round(call.latencyMs)}ms</td>
                    <td className="py-2 pr-3">
                      <span className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground">
                        <Activity className="h-3 w-3" aria-hidden="true" />
                        {call.success ? "success" : "failed"}
                        {call.fallbackUsed ? " / fallback" : ""}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!recentCalls.length ? <p className="py-8 text-center text-sm text-muted-foreground">No recent LLM calls.</p> : null}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
