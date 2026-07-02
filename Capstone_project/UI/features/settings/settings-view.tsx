"use client";

import { Settings } from "lucide-react";
import { LLMProviderSettings } from "@/components/forms/llm-provider-settings";
import { SettingsForm } from "@/components/forms/settings-form";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { useSettings } from "@/hooks/use-settings";

export function SettingsView() {
  const { data, error, isLoading, refetch } = useSettings();

  if (isLoading) {
    return <LoadingState label="Loading settings" />;
  }

  if (error) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Settings}
        eyebrow="Settings"
        title="Settings & controls"
        description="Choose which AI models to use, set how sure the AI must be before clearing a case, and turn safety controls on or off."
        actions={
          <Button variant="secondary">
            <Settings className="h-4 w-4" aria-hidden="true" />
            Change history
          </Button>
        }
      />

      <LLMProviderSettings />

      {data ? (
        <SettingsForm settings={data} />
      ) : (
        <EmptyState
          title="Settings endpoint unavailable"
          description="Governance settings will be editable after the backend exposes persisted configuration."
          icon={Settings}
        />
      )}
    </div>
  );
}
