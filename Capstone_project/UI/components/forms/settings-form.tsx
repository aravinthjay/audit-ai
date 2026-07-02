"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { settingsSchema, type SettingsForm as SettingsFormValues } from "@/types/forms";
import type { AppSettings } from "@/types/domain";

export function SettingsForm({ settings }: { settings: AppSettings }) {
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: settings,
  });

  useEffect(() => {
    reset(settings);
  }, [reset, settings]);

  function onSubmit() {
    setSavedAt(new Date().toLocaleTimeString());
  }

  return (
    <form className="grid gap-4 xl:grid-cols-[1fr_360px]" onSubmit={handleSubmit(onSubmit)}>
      <Card>
        <CardHeader>
          <CardTitle>Model and threshold policy</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="reasoningModel" className="text-sm font-medium text-foreground">
              Reasoning model
            </label>
            <Input id="reasoningModel" className="mt-2" {...register("reasoningModel")} />
            {errors.reasoningModel ? <p className="mt-1 text-xs text-danger-foreground">{errors.reasoningModel.message}</p> : null}
          </div>
          <div>
            <label htmlFor="reportModel" className="text-sm font-medium text-foreground">
              Report model
            </label>
            <Input id="reportModel" className="mt-2" {...register("reportModel")} />
            {errors.reportModel ? <p className="mt-1 text-xs text-danger-foreground">{errors.reportModel.message}</p> : null}
          </div>
          <div>
            <label htmlFor="autoClearThreshold" className="text-sm font-medium text-foreground">
              Auto-clear threshold
            </label>
            <Input
              id="autoClearThreshold"
              className="mt-2"
              step="0.01"
              type="number"
              {...register("autoClearThreshold", { valueAsNumber: true })}
            />
            {errors.autoClearThreshold ? (
              <p className="mt-1 text-xs text-danger-foreground">{errors.autoClearThreshold.message}</p>
            ) : null}
          </div>
          <div>
            <label htmlFor="reviewerThreshold" className="text-sm font-medium text-foreground">
              Reviewer threshold
            </label>
            <Input
              id="reviewerThreshold"
              className="mt-2"
              step="0.01"
              type="number"
              {...register("reviewerThreshold", { valueAsNumber: true })}
            />
            {errors.reviewerThreshold ? (
              <p className="mt-1 text-xs text-danger-foreground">{errors.reviewerThreshold.message}</p>
            ) : null}
          </div>
          <div>
            <label htmlFor="materiality" className="text-sm font-medium text-foreground">
              Materiality
            </label>
            <Input id="materiality" className="mt-2" type="number" {...register("materiality", { valueAsNumber: true })} />
            {errors.materiality ? <p className="mt-1 text-xs text-danger-foreground">{errors.materiality.message}</p> : null}
          </div>
          <div>
            <label htmlFor="displayCurrency" className="text-sm font-medium text-foreground">
              Display currency
            </label>
            <Input id="displayCurrency" className="mt-2 uppercase" maxLength={3} {...register("displayCurrency")} />
            {errors.displayCurrency ? <p className="mt-1 text-xs text-danger-foreground">{errors.displayCurrency.message}</p> : null}
          </div>
          <div>
            <label htmlFor="estimatedAgentRunCostUsd" className="text-sm font-medium text-foreground">
              Estimated crew cost
            </label>
            <Input
              id="estimatedAgentRunCostUsd"
              className="mt-2"
              step="0.01"
              type="number"
              {...register("estimatedAgentRunCostUsd", { valueAsNumber: true })}
            />
            {errors.estimatedAgentRunCostUsd ? (
              <p className="mt-1 text-xs text-danger-foreground">{errors.estimatedAgentRunCostUsd.message}</p>
            ) : null}
          </div>
          <div>
            <label htmlFor="debateRoundCap" className="text-sm font-medium text-foreground">
              Debate round cap
            </label>
            <Input
              id="debateRoundCap"
              className="mt-2"
              type="number"
              {...register("debateRoundCap", { valueAsNumber: true })}
            />
            {errors.debateRoundCap ? <p className="mt-1 text-xs text-danger-foreground">{errors.debateRoundCap.message}</p> : null}
          </div>
          <div>
            <label htmlFor="apiKeyVault" className="text-sm font-medium text-foreground">
              API key vault
            </label>
            <Input id="apiKeyVault" className="mt-2" {...register("apiKeyVault")} />
            {errors.apiKeyVault ? <p className="mt-1 text-xs text-danger-foreground">{errors.apiKeyVault.message}</p> : null}
          </div>
          <label className="text-sm font-medium text-foreground">
            Theme
            <select className="mt-2 h-9 w-full rounded-md border border-input bg-background px-3 text-sm" {...register("theme")}>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Controls</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-start gap-3 rounded-md border border-border bg-background p-3 text-sm text-muted-foreground">
            <input className="mt-1" type="checkbox" {...register("segregationOfDuties")} />
            <span>
              <span className="block font-medium text-foreground">Segregation of duties</span>
              Enforce independent reviewer assignment for high-risk conclusions.
            </span>
          </label>
          <label className="flex items-start gap-3 rounded-md border border-border bg-background p-3 text-sm text-muted-foreground">
            <input className="mt-1" type="checkbox" {...register("immutableAuditLog")} />
            <span>
              <span className="block font-medium text-foreground">Immutable audit log</span>
              Lock every agent action, evidence version, and reviewer decision.
            </span>
          </label>
          <label className="flex items-start gap-3 rounded-md border border-border bg-background p-3 text-sm text-muted-foreground">
            <input className="mt-1" type="checkbox" {...register("notifications")} />
            <span>
              <span className="block font-medium text-foreground">Notifications</span>
              Notify reviewers when cases pause at human interrupt.
            </span>
          </label>
          <label className="flex items-start gap-3 rounded-md border border-border bg-background p-3 text-sm text-muted-foreground">
            <input className="mt-1" type="checkbox" {...register("ipAllowlist")} />
            <span>
              <span className="block font-medium text-foreground">Security allowlist</span>
              Restrict reviewer and admin actions to approved network ranges.
            </span>
          </label>
          <div>
            <label htmlFor="auditRetentionYears" className="text-sm font-medium text-foreground">
              Audit retention years
            </label>
            <Input
              id="auditRetentionYears"
              className="mt-2"
              type="number"
              {...register("auditRetentionYears", { valueAsNumber: true })}
            />
            {errors.auditRetentionYears ? (
              <p className="mt-1 text-xs text-danger-foreground">{errors.auditRetentionYears.message}</p>
            ) : null}
          </div>

          {savedAt ? (
            <p className="rounded-md border border-success-border bg-success-soft px-3 py-2 text-sm text-success-foreground">
              Settings staged at {savedAt}
            </p>
          ) : null}

          <Button className="w-full" type="submit" disabled={isSubmitting}>
            Save policy
          </Button>
        </CardContent>
      </Card>
    </form>
  );
}
