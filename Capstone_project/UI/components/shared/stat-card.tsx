import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type StatCardProps = {
  label: string;
  value: string;
  helper: string;
  icon: LucideIcon;
  tone?: "default" | "success" | "warning" | "danger";
};

const toneClass: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "text-primary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
};

export function StatCard({ label, value, helper, icon: Icon, tone = "default" }: StatCardProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
          <Icon className={cn("h-4 w-4", toneClass[tone])} aria-hidden="true" />
        </div>
        <p className="mt-3 text-2xl font-semibold text-foreground">{value}</p>
        <p className={cn("mt-1 text-xs", toneClass[tone])}>{helper}</p>
      </CardContent>
    </Card>
  );
}
