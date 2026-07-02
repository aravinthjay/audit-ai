import { AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { VerificationClaim } from "@/types/domain";

const statusMeta = {
  grounded: { icon: CheckCircle2, label: "Grounded", badge: "success" },
  unsupported: { icon: AlertTriangle, label: "Unsupported", badge: "danger" },
  missing: { icon: HelpCircle, label: "Missing source", badge: "warning" },
} as const;

export function VerificationClaimCard({ claim }: { claim: VerificationClaim }) {
  const meta = statusMeta[claim.status];
  const Icon = meta.icon;

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Icon className="mt-0.5 h-5 w-5 text-primary" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground">{claim.claim}</h2>
              <Badge variant={meta.badge}>{meta.label}</Badge>
            </div>
            <p className="mt-2 font-mono text-xs text-muted-foreground">{claim.citation}</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              <span className="font-medium text-foreground">Supporting evidence:</span> {claim.supportingEvidence}
            </p>
            <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
              <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
                Pass <span className="font-mono text-foreground">{claim.pass.replace("_", " ")}</span>
              </div>
              <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
                Action <span className="font-mono text-foreground">{claim.action}</span>
              </div>
              <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
                Owner <span className="font-mono text-foreground">{claim.owner}</span>
              </div>
            </div>
            <p className="mt-3 rounded-md border border-border bg-background px-3 py-2 text-xs leading-5 text-muted-foreground">
              {claim.notes}
            </p>
            <ConfidenceMeter value={claim.confidence} className="mt-4" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
