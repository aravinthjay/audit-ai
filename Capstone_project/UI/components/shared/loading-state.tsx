import { Loader2 } from "lucide-react";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div className="animate-surface-in flex min-h-64 flex-col items-center justify-center rounded-lg border border-border bg-card p-8 text-muted-foreground shadow-card">
      <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
      <span className="mt-3 text-sm">{label}</span>
      <div className="mt-5 grid w-full max-w-md gap-2" aria-hidden="true">
        <div className="h-2 animate-pulse rounded-full bg-muted" />
        <div className="h-2 w-4/5 animate-pulse rounded-full bg-muted" />
        <div className="h-2 w-2/3 animate-pulse rounded-full bg-muted" />
      </div>
    </div>
  );
}
