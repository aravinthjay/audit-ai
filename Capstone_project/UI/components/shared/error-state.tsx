import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { friendlyError } from "@/lib/friendly-error";

type ErrorStateProps = {
  title?: string;
  description?: string;
  /** Raw error (string/Error). Rendered as a clear message + collapsible details. */
  error?: unknown;
  onRetry?: () => void;
};

function errorText(error: unknown): string {
  if (!error) return "";
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  return String(error);
}

export function ErrorState({
  title = "Unable to load data",
  description = "The workspace could not retrieve the requested data.",
  error,
  onRetry,
}: ErrorStateProps) {
  const raw = errorText(error);
  const friendly = raw ? friendlyError(raw) : null;
  const heading = friendly?.title || title;
  const body = friendly?.detail || description;

  return (
    <section className="animate-surface-in rounded-lg border border-danger-border bg-danger-soft p-5 text-danger-foreground shadow-card">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5" aria-hidden="true" />
        <div className="min-w-0">
          <h2 className="text-sm font-semibold">{heading}</h2>
          <p className="mt-1 text-sm text-danger-foreground/80">{body}</p>
          {raw && friendly && friendly.detail !== raw ? (
            <details className="mt-2">
              <summary className="cursor-pointer text-xs text-danger-foreground/70">Technical details</summary>
              <pre className="mt-1 max-w-full overflow-x-auto whitespace-pre-wrap break-words text-[11px] text-danger-foreground/70">
                {raw}
              </pre>
            </details>
          ) : null}
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
