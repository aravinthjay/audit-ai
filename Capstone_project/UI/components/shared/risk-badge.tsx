import { Badge } from "@/components/ui/badge";
import { riskLabel, riskTone } from "@/lib/status";
import type { RiskLevel } from "@/types/domain";

type BadgeTone = "default" | "primary" | "success" | "warning" | "danger" | "info";

export function RiskBadge({ risk }: { risk: RiskLevel }) {
  const toneMap: Record<ReturnType<typeof riskTone>, BadgeTone> = {
    danger: "danger",
    warning: "warning",
    success: "success",
    muted: "default",
  };

  return <Badge variant={toneMap[riskTone(risk)]}>{riskLabel(risk)}</Badge>;
}
