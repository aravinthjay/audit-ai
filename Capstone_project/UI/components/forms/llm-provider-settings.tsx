"use client";

import { AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useLlmSettings, useUpdateLlmSettings } from "@/hooks/use-settings";
import type { LLMProviderName } from "@/types/domain";

const providerIds: LLMProviderName[] = ["anthropic", "groq", "openai", "gemini"];

function normalizeFallbackOrder(defaultProvider: LLMProviderName, order: LLMProviderName[]) {
  const next = order.filter((provider, index) => provider !== defaultProvider && order.indexOf(provider) === index);
  for (const provider of providerIds) {
    if (provider !== defaultProvider && !next.includes(provider)) {
      next.push(provider);
    }
  }
  return next;
}

export function LLMProviderSettings() {
  const query = useLlmSettings();
  const mutation = useUpdateLlmSettings();
  const [defaultProvider, setDefaultProvider] = useState<LLMProviderName>("anthropic");
  const [fallbackEnabled, setFallbackEnabled] = useState(true);
  const [fallbackOrder, setFallbackOrder] = useState<LLMProviderName[]>(["groq", "openai"]);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    if (!query.data) {
      return;
    }
    setDefaultProvider(query.data.defaultProvider);
    setFallbackEnabled(query.data.fallbackEnabled);
    setFallbackOrder(normalizeFallbackOrder(query.data.defaultProvider, query.data.fallbackOrder));
  }, [query.data]);

  const providers = query.data?.providers ?? [];
  const selectedProvider = providers.find((provider) => provider.id === defaultProvider);
  const orderedFallbacks = useMemo(
    () => normalizeFallbackOrder(defaultProvider, fallbackOrder),
    [defaultProvider, fallbackOrder],
  );

  function moveFallback(provider: LLMProviderName, direction: -1 | 1) {
    const current = normalizeFallbackOrder(defaultProvider, fallbackOrder);
    const index = current.indexOf(provider);
    const nextIndex = index + direction;
    if (index < 0 || nextIndex < 0 || nextIndex >= current.length) {
      return;
    }
    const next = [...current];
    [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
    setFallbackOrder(next);
  }

  function saveSettings() {
    setSavedAt(null);
    mutation.mutate(
      {
        defaultProvider,
        fallbackEnabled,
        fallbackOrder: orderedFallbacks,
      },
      {
        onSuccess: () => setSavedAt(new Date().toLocaleTimeString()),
      },
    );
  }

  if (query.isLoading) {
    return <LoadingState label="Loading LLM provider settings" />;
  }

  if (query.error) {
    return <ErrorState title="Unable to load LLM settings" onRetry={() => void query.refetch()} />;
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-primary-soft via-card to-info-soft">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>LLM provider routing</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Switch default providers and control automatic fallback without exposing API keys to the browser.
            </p>
          </div>
          <span className="inline-flex w-fit items-center gap-2 rounded-md border border-primary-border bg-card px-2.5 py-1 text-xs font-medium text-primary">
            Active: {selectedProvider?.label ?? defaultProvider}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
          <div className="space-y-4">
            <label htmlFor="llm-provider" className="block text-sm font-medium text-foreground">
              Default provider
            </label>
            <select
              id="llm-provider"
              value={defaultProvider}
              onChange={(event) => {
                const next = event.target.value as LLMProviderName;
                setDefaultProvider(next);
                setFallbackOrder((current) => normalizeFallbackOrder(next, current));
              }}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground shadow-sm transition-colors focus:border-primary"
            >
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.label}
                </option>
              ))}
            </select>

            {selectedProvider && !selectedProvider.configured ? (
              <div className="flex items-start gap-2 rounded-md border border-warning-border bg-warning-soft p-3 text-sm text-warning-foreground">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <p>
                  {selectedProvider.label} is missing {selectedProvider.missingEnv}. Add it to the backend environment
                  before saving this provider.
                </p>
              </div>
            ) : null}

            <label className="flex items-start gap-3 rounded-md border border-border bg-background p-3 text-sm text-muted-foreground shadow-sm">
              <input
                className="mt-1"
                type="checkbox"
                checked={fallbackEnabled}
                onChange={(event) => setFallbackEnabled(event.target.checked)}
              />
              <span>
                <span className="block font-medium text-foreground">Automatic fallback</span>
                Retry context, token, rate-limit, timeout, and quota failures on the next configured provider.
              </span>
            </label>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium text-foreground">Provider status</p>
            <div className="grid gap-3 sm:grid-cols-3">
              {providers.map((provider) => (
                <div
                  key={provider.id}
                  className={cn(
                    "rounded-md border p-3 transition-all",
                    provider.configured
                      ? "border-success-border bg-success-soft/60"
                      : "border-border bg-muted/50",
                  )}
                >
                  <div className="flex items-center gap-2">
                    {provider.configured ? (
                      <CheckCircle2 className="h-4 w-4 text-success-foreground" aria-hidden="true" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-warning-foreground" aria-hidden="true" />
                    )}
                    <p className="truncate text-sm font-medium text-foreground">{provider.label}</p>
                  </div>
                  <p className="mt-2 truncate text-xs text-muted-foreground">{provider.reasoningModel}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {provider.configured ? "API key configured" : `Missing ${provider.missingEnv}`}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-md border border-border bg-muted/40 p-4">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-foreground">Fallback order</p>
              <p className="text-xs text-muted-foreground">Used only when automatic fallback is enabled.</p>
            </div>
          </div>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {orderedFallbacks.map((providerId, index) => {
              const provider = providers.find((item) => item.id === providerId);
              return (
                <div
                  key={providerId}
                  className="flex items-center gap-3 rounded-md border border-border bg-card p-3 shadow-sm"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary-soft text-xs font-semibold text-primary">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">{provider?.label ?? providerId}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {provider?.configured ? "ready" : `missing ${provider?.missingEnv ?? "API key"}`}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Move ${provider?.label ?? providerId} up`}
                    disabled={index === 0}
                    onClick={() => moveFallback(providerId, -1)}
                  >
                    <ArrowUp className="h-4 w-4" aria-hidden="true" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Move ${provider?.label ?? providerId} down`}
                    disabled={index === orderedFallbacks.length - 1}
                    onClick={() => moveFallback(providerId, 1)}
                  >
                    <ArrowDown className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              );
            })}
          </div>
        </div>

        {mutation.error ? (
          <div className="rounded-md border border-danger-border bg-danger-soft px-3 py-2 text-sm text-danger-foreground">
            {mutation.error instanceof Error ? mutation.error.message : "Unable to save LLM settings."}
          </div>
        ) : null}
        {savedAt ? (
          <div className="rounded-md border border-success-border bg-success-soft px-3 py-2 text-sm text-success-foreground">
            LLM settings saved at {savedAt}
          </div>
        ) : null}

        <div className="flex justify-end">
          <Button type="button" onClick={saveSettings} disabled={mutation.isPending}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {mutation.isPending ? "Saving..." : "Save LLM settings"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
