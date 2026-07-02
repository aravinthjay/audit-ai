import { Progress } from "@/components/ui/progress";
import { cn, formatPercent } from "@/lib/utils";

type ConfidenceMeterProps = {
  value: number;
  label?: string;
  className?: string;
};

export function ConfidenceMeter({ value, label = "Confidence", className }: ConfidenceMeterProps) {
  const tone = value >= 0.9 ? "success" : value >= 0.75 ? "warning" : "danger";

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono text-foreground">{formatPercent(value)}</span>
      </div>
      <Progress value={value} tone={tone} />
    </div>
  );
}
