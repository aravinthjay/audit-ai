import { cn } from "@/lib/utils";

export function ChartSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex w-full animate-pulse items-center justify-center rounded-lg border border-border bg-card text-xs text-muted-foreground",
        className ?? "h-72",
      )}
      aria-hidden="true"
    >
      Loading visualization...
    </div>
  );
}
