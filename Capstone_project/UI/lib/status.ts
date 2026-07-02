import type { RiskLevel, WorkState } from "@/types/domain";

export function riskLabel(risk: RiskLevel) {
  const labels: Record<RiskLevel, string> = {
    critical: "Critical",
    high: "High",
    medium: "Medium",
    low: "Low",
    cleared: "Cleared",
  };

  return labels[risk];
}

export function riskTone(risk: RiskLevel) {
  const tones: Record<RiskLevel, "danger" | "warning" | "success" | "muted"> = {
    critical: "danger",
    high: "danger",
    medium: "warning",
    low: "success",
    cleared: "success",
  };

  return tones[risk];
}

export function stateTone(state: WorkState) {
  const tones: Record<WorkState, "success" | "warning" | "danger" | "primary" | "muted" | "info"> = {
    done: "success",
    running: "primary",
    queued: "info",
    idle: "muted",
    challenger: "danger",
    review: "warning",
    blocked: "danger",
    failed: "danger",
    retry: "warning",
    escalated: "warning",
  };

  return tones[state];
}

export function statusLabel(status: string) {
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
