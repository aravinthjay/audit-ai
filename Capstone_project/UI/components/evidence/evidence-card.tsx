import { FileText } from "lucide-react";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { EvidenceSource } from "@/types/domain";

export function EvidenceCard({ evidence }: { evidence: EvidenceSource }) {
  const qualityTone = {
    strong: "success",
    adequate: "warning",
    weak: "danger",
    missing: "danger",
  } as const;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-primary-border bg-primary-soft text-primary">
            <FileText className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="break-words text-sm font-semibold text-foreground">{evidence.title}</h2>
              <Badge variant="info">{evidence.type}</Badge>
              <Badge variant={qualityTone[evidence.quality]}>{evidence.quality}</Badge>
            </div>
            <p className="mt-2 break-words text-sm leading-6 text-muted-foreground">{evidence.summary}</p>
            <div className="mt-3 break-words rounded-md border border-border bg-muted/40 px-3 py-2 text-xs leading-5 text-muted-foreground">
              <span className="font-medium text-foreground">Document preview:</span> {evidence.preview}
            </div>
          </div>
        </div>
        <div className="mt-4 grid gap-3 text-xs text-muted-foreground sm:grid-cols-2">
          <div className="min-w-0">
            <span className="block text-muted-foreground">Citation</span>
            <span className="break-all font-mono text-foreground">{evidence.citation}</span>
          </div>
          <div className="min-w-0">
            <span className="block text-muted-foreground">Last verified</span>
            <span className="break-all text-foreground">{evidence.lastVerified}</span>
          </div>
          <div className="min-w-0">
            <span className="block text-muted-foreground">Version</span>
            <span className="break-all font-mono text-foreground">{evidence.version}</span>
          </div>
          <div className="min-w-0">
            <span className="block text-muted-foreground">Owner</span>
            <span className="break-words text-foreground">{evidence.owner}</span>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {evidence.tags.map((tag) => (
            <Badge key={tag}>{tag}</Badge>
          ))}
        </div>
        <ConfidenceMeter value={evidence.confidence} className="mt-4" />
      </CardContent>
    </Card>
  );
}
