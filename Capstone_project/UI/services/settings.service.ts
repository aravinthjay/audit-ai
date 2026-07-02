import { apiRequest } from "@/services/api";
import type {
  AppSettings,
  LLMProviderName,
  LLMProviderStatus,
  LLMSettings,
  LLMSettingsUpdate,
} from "@/types/domain";

type ApiAppSettings = {
  reasoning_model: string;
  report_model: string;
  auto_clear_threshold: number;
  reviewer_threshold: number;
  materiality: number;
  segregation_of_duties: boolean;
  immutable_audit_log: boolean;
  debate_round_cap: number;
  api_key_vault: string;
  theme: AppSettings["theme"];
  display_currency: string;
  notifications: boolean;
  audit_retention_years: number;
  ip_allowlist: boolean;
  estimated_agent_run_cost_usd: number;
};

type ApiLLMProviderStatus = {
  id: LLMProviderName;
  label: string;
  configured: boolean;
  reasoning_model: string;
  lightweight_model: string;
  missing_env?: string | null;
};

type ApiLLMSettings = {
  default_provider: LLMProviderName;
  active_provider: LLMProviderName;
  fallback_enabled: boolean;
  fallback_order: LLMProviderName[];
  providers: ApiLLMProviderStatus[];
};

function mapSettings(settings: ApiAppSettings): AppSettings {
  return {
    reasoningModel: settings.reasoning_model,
    reportModel: settings.report_model,
    autoClearThreshold: settings.auto_clear_threshold,
    reviewerThreshold: settings.reviewer_threshold,
    materiality: settings.materiality,
    segregationOfDuties: settings.segregation_of_duties,
    immutableAuditLog: settings.immutable_audit_log,
    debateRoundCap: settings.debate_round_cap,
    apiKeyVault: settings.api_key_vault,
    theme: settings.theme,
    displayCurrency: settings.display_currency,
    notifications: settings.notifications,
    auditRetentionYears: settings.audit_retention_years,
    ipAllowlist: settings.ip_allowlist,
    estimatedAgentRunCostUsd: settings.estimated_agent_run_cost_usd,
  };
}

function mapProvider(provider: ApiLLMProviderStatus): LLMProviderStatus {
  return {
    id: provider.id,
    label: provider.label,
    configured: provider.configured,
    reasoningModel: provider.reasoning_model,
    lightweightModel: provider.lightweight_model,
    missingEnv: provider.missing_env,
  };
}

function mapLlmSettings(settings: ApiLLMSettings): LLMSettings {
  return {
    defaultProvider: settings.default_provider,
    activeProvider: settings.active_provider,
    fallbackEnabled: settings.fallback_enabled,
    fallbackOrder: settings.fallback_order,
    providers: settings.providers.map(mapProvider),
  };
}

export async function getSettings(): Promise<AppSettings> {
  return mapSettings(await apiRequest<ApiAppSettings>("/settings"));
}

export async function updateSettings(payload: AppSettings): Promise<AppSettings> {
  const body: ApiAppSettings = {
    reasoning_model: payload.reasoningModel,
    report_model: payload.reportModel,
    auto_clear_threshold: payload.autoClearThreshold,
    reviewer_threshold: payload.reviewerThreshold,
    materiality: payload.materiality,
    segregation_of_duties: payload.segregationOfDuties,
    immutable_audit_log: payload.immutableAuditLog,
    debate_round_cap: payload.debateRoundCap,
    api_key_vault: payload.apiKeyVault,
    theme: payload.theme,
    display_currency: payload.displayCurrency,
    notifications: payload.notifications,
    audit_retention_years: payload.auditRetentionYears,
    ip_allowlist: payload.ipAllowlist,
    estimated_agent_run_cost_usd: payload.estimatedAgentRunCostUsd,
  };

  return mapSettings(
    await apiRequest<ApiAppSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  );
}

export async function getLlmSettings(): Promise<LLMSettings> {
  return mapLlmSettings(await apiRequest<ApiLLMSettings>("/settings/llm"));
}

export async function updateLlmSettings(payload: LLMSettingsUpdate): Promise<LLMSettings> {
  return mapLlmSettings(
    await apiRequest<ApiLLMSettings>("/settings/llm", {
      method: "PUT",
      body: JSON.stringify({
        default_provider: payload.defaultProvider,
        fallback_enabled: payload.fallbackEnabled,
        fallback_order: payload.fallbackOrder,
      }),
    }),
  );
}

export async function getLlmProviders(): Promise<LLMProviderStatus[]> {
  const providers = await apiRequest<ApiLLMProviderStatus[]>("/settings/llm/providers");
  return providers.map(mapProvider);
}
