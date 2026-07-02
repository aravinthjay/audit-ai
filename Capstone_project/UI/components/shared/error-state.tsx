import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

type ErrorStateProps = {
  title?: string;
  description?: string;
  onRetry?: () => void;
};

export function ErrorState({
  title = "Unable to load data",
  description = "The workspace could not retrieve the requested data.",
  onRetry,
}: ErrorStateProps) {
  return (
    <section className="animate-surface-in rounded-lg border border-danger-border bg-danger-soft p-5 text-danger-foreground shadow-card">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5" aria-hidden="true" />
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          <p className="mt-1 text-sm text-danger-foreground/80">{description}</p>
          {onRetry ? (
            <Button className="mt-4" variant="danger" size="sm" onClick={onRetry}>
              Retry
            </Button>
          ) : null}
        </div>
      </div>
    </section>
  );
}
