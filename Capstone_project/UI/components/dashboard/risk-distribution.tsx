import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { riskLabel } from "@/lib/status";
import type { DashboardSummary } from "@/types/domain";

type Tone = "success" | "warning" | "danger" | "info";

const riskTone: Record<string, Tone> = {
  critical: "danger",
  high: "danger",
  medium: "warning",
  low: "success",
  cleared: "info",
};

export function RiskDistribution({ summary }: { summary: DashboardSummary }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Risk distribution</CardTitle>
        <span className="text-xs text-muted-foreground">Flagged transactions / population</span>
      </CardHeader>
      <CardContent className="space-y-4">
        {summary.riskDistribution.map((item) => (
          <div key={item.label}>
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{riskLabel(item.label)}</span>
              <span className="font-mono text-foreground">{item.count}</span>
            </div>
            <Progress value={item.percent} tone={riskTone[item.label]} />
          </div>
        ))}

        <div className="grid grid-cols-3 gap-3 border-t border-border pt-4">
          <div>
            <p className="text-xs text-muted-foreground">Auto-cleared</p>
            <p className="mt-1 font-mono text-lg text-success-foreground">{summary.throughput.autoCleared}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">In review</p>
            <p className="mt-1 font-mono text-lg text-warning-foreground">{summary.throughput.inReview}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Manual</p>
            <p className="mt-1 font-mono text-lg text-danger-foreground">{summary.throughput.manual}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
