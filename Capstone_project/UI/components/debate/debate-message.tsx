import { Gavel, ShieldAlert, ShieldCheck } from "lucide-react";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { DebateArgument } from "@/types/domain";

export function DebateMessage({ argument }: { argument: DebateArgument }) {
  const challenger = argument.side === "challenger";
  const adjudicator = argument.side === "adjudicator";
  const Icon = challenger ? ShieldAlert : adjudicator ? Gavel : ShieldCheck;

  return (
    <Card
      className={cn(
        challenger
          ? "border-danger-border"
          : adjudicator
            ? "border-primary-border"
            : "border-success-border",
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-md border",
              challenger
                ? "border-danger-border bg-danger-soft text-danger-foreground"
                : adjudicator
                  ? "border-primary-border bg-primary-soft text-primary"
                : "border-success-border bg-success-soft text-success-foreground",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground">{argument.title}</h2>
              <Badge variant={challenger ? "danger" : adjudicator ? "primary" : "success"}>{argument.side}</Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{argument.timestamp}</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{argument.summary}</p>
            {typeof argument.confidence === "number" ? (
              <ConfidenceMeter
                value={argument.confidence}
                label={adjudicator ? "Verdict confidence" : "Confidence"}
                className="mt-4"
              />
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              {argument.tags.map((tag) => (
                <Badge key={tag}>{tag}</Badge>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {argument.citations.map((citation) => (
                <Badge key={citation} variant="primary">
                  {citation}
                </Badge>
              ))}
            </div>
            <details className="mt-3 text-xs text-muted-foreground">
              <summary className="cursor-pointer text-primary">Expand transcript detail</summary>
              <p className="mt-2 leading-5">{argument.details}</p>
            </details>
            <div className="mt-4 flex flex-col gap-2 border-t border-border pt-3 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
              <span>{argument.footer}</span>
              <span className="font-mono text-foreground">{argument.scoreLabel}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
