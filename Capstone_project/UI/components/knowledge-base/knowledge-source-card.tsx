import { Database } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { KnowledgeSource } from "@/types/domain";

const statusTone = {
  synced: "success",
  review_needed: "warning",
  stale: "danger",
} as const;

export function KnowledgeSourceCard({ source }: { source: KnowledgeSource }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-primary-border bg-primary-soft text-primary">
            <Database className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground">{source.title}</h2>
              <Badge variant={statusTone[source.status]}>{source.status.replace("_", " ")}</Badge>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{source.description}</p>
            <div className="mt-3 rounded-md border border-border bg-muted/40 px-3 py-2 text-xs leading-5 text-muted-foreground">
              <span className="font-medium text-foreground">Clause preview:</span> {source.clausePreview}
            </div>
            <div className="mt-4 grid gap-3 text-xs text-muted-foreground sm:grid-cols-3">
              <div>
                <span className="block">Owner</span>
                <span className="font-medium text-foreground">{source.owner}</span>
              </div>
              <div>
                <span className="block">Coverage</span>
                <span className="font-mono text-foreground">{source.count}</span>
              </div>
              <div>
                <span className="block">Freshness</span>
                <span className="text-foreground">{source.freshness}</span>
              </div>
              <div>
                <span className="block">Embedding</span>
                <span className="font-mono text-foreground">{source.embeddingStatus}</span>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {source.citationIds.map((citation) => (
                <Badge key={citation} variant="primary">
                  {citation}
                </Badge>
              ))}
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              Versions: <span className="font-mono text-foreground">{source.versionHistory.join(" / ")}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
