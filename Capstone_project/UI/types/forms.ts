import { z } from "zod";

export const reviewDecisionSchema = z.object({
  decision: z.enum(["approve", "reject", "request_evidence", "escalate"]),
  comment: z.string().min(16, "Add enough context for the audit trail."),
  signature: z.string().min(3, "Add a reviewer signature."),
});

export type ReviewDecisionForm = z.infer<typeof reviewDecisionSchema>;

export const settingsSchema = z.object({
  reasoningModel: z.string().min(1),
  reportModel: z.string().min(1),
  autoClearThreshold: z.number().min(0.5).max(0.99),
  reviewerThreshold: z.number().min(0.5).max(0.95),
  materiality: z.number().min(1_000).max(1_000_000),
  segregationOfDuties: z.boolean(),
  immutableAuditLog: z.boolean(),
  debateRoundCap: z.number().min(1).max(5),
  apiKeyVault: z.string().min(1),
  theme: z.enum(["system", "light", "dark"]),
  displayCurrency: z.string().length(3),
  notifications: z.boolean(),
  auditRetentionYears: z.number().min(1).max(10),
  ipAllowlist: z.boolean(),
  estimatedAgentRunCostUsd: z.number().min(0).max(100),
});

export type SettingsForm = z.infer<typeof settingsSchema>;
