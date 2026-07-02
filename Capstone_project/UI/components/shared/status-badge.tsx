import { Badge } from "@/components/ui/badge";
import { stateTone, statusLabel } from "@/lib/status";
import type { WorkState } from "@/types/domain";

type BadgeTone = "default" | "primary" | "success" | "warning" | "danger" | "info";

export function StatusBadge({ state }: { state: WorkState }) {
  const toneMap: Record<ReturnType<typeof stateTone>, BadgeTone> = {
    success: "success",
    warning: "warning",
    danger: "danger",
    primary: "primary",
    muted: "default",
    info: "info",
  };

  return <Badge variant={toneMap[stateTone(state)]}>{statusLabel(state)}</Badge>;
}

export function WorkflowStatusBadge({ status }: { status: string }) {
  return <Badge variant="info">{statusLabel(status)}</Badge>;
}
