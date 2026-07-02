"use client";

import { AlertTriangle, CircleHelp, Clock3, RefreshCw, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { EvidenceVerification, EvidenceVerificationStatus } from "@/types/domain";

type EvidenceVerificationCardProps = {
  verification?: EvidenceVerification | null;
  isLoading?: boolean;
  error?: unknown;
  isReverifying?: boolean;
  onReverify?: () => void;
};

const statusMeta: Record<
  EvidenceVerificationStatus,
  {
    label: string;
    badge: "success" | "danger" | "warning" | "default";
    icon: typeof ShieldCheck;
  }
> = {
  VERIFIED: { label: "Verified", badge: "success", icon: ShieldCheck },
  FLAGGED: { label: "Flagged", badge: "danger", icon: AlertTriangle },
  API_UNAVAILABLE: { label: "API unavailable", badge: "warning", icon: Clock3 },
  NEEDS_MANUAL_REVIEW: { label: "Manual review", badge: "default", icon: CircleHelp },
};

function amount(value?: number | null) {
  return typeof value === "number" ? formatCurrency(value) : "Unavailable";
}

function percent(value?: number | null) {
  return typeof value === "number" ? formatPercent(value) : "Unavailable";
}

function dateTime(value?: string) {
  if (!value) {
    return "Not verified";
  }

  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function EvidenceVerificationCard({
  verification,
  isLoading = false,
  error,
  isReverifying = false,
  onReverify,
}: EvidenceVerificationCardProps) {
  const meta = verification ? statusMeta[verification.verificationStatus] : null;
  const Icon = meta?.icon ?? CircleHelp;

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Third-party evidence verification</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">
            Claimed amount compared with category-specific external benchmark data.
          </p>
        </div>
        <Button size="sm" variant="secondary" disabled={isLoading || isReverifying} onClick={onReverify}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          {isReverifying ? "Verifying..." : "Re-verify"}
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="rounded-md border border-border bg-muted/40 px-3 py-4 text-sm text-muted-foreground">
            Loading third-party verification.
          </div>
        ) : error ? (
          <div className="rounded-md border border-warning-border bg-warning-soft px-3 py-4 text-sm text-warning-foreground">
            Evidence verification could not be loaded. Re-run verification or check the provider configuration.
          </div>
        ) : verification && meta ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-3">
                <Icon className="mt-0.5 h-5 w-5 text-primary" aria-hidden="true" />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={meta.badge}>{meta.label}</Badge>
                    <span className="break-all font-mono text-xs text-muted-foreground">
                      {verification.providerName}
                    </span>
                  </div>
                  <p className="mt-2 break-words text-sm leading-6 text-muted-foreground">{verification.reason}</p>
                </div>
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <p>Last verified</p>
                <p className="break-all font-mono text-foreground">{dateTime(verification.updatedAt)}</p>
              </div>
            </div>

            {verification.verificationStatus === "FLAGGED" ? (
              <div className="rounded-md border border-danger-border bg-danger-soft px-3 py-2 text-sm text-danger-foreground">
                Claimed amount is outside the accepted +/-{Math.round(verification.tolerancePercentage * 100)}% range. Manual review required.
              </div>
            ) : null}

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              <Metric label="Claimed amount" value={amount(verification.claimedAmount)} />
              <Metric label="Third-party amount" value={amount(verification.fetchedAmount)} />
              <Metric
                label="Difference"
                value={
                  typeof verification.differenceAmount === "number"
                    ? `${amount(verification.differenceAmount)} (${percent(verification.differencePercentage)})`
                    : "Unavailable"
                }
              />
              <Metric
                label="Allowed range"
                value={
                  typeof verification.minAcceptableAmount === "number" &&
                  typeof verification.maxAcceptableAmount === "number"
                    ? `${amount(verification.minAcceptableAmount)} - ${amount(verification.maxAcceptableAmount)}`
                    : "Unavailable"
                }
              />
              <Metric label="Status" value={meta.label} />
            </div>

            <div className="grid gap-3 text-xs text-muted-foreground sm:grid-cols-3">
              <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
                Category <span className="break-all font-mono text-foreground">{verification.category}</span>
              </div>
              <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
                Tolerance <span className="break-all font-mono text-foreground">{percent(verification.tolerancePercentage)}</span>
              </div>
              <div className="min-w-0 rounded-md border border-border bg-background px-3 py-2">
                Confidence <span className="break-all font-mono text-foreground">{percent(verification.confidenceScore)}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-border bg-muted/30 px-3 py-4 text-sm text-muted-foreground">
            No third-party evidence verification has been recorded for this claim yet.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-h-[76px] rounded-md border border-border bg-background px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-2 break-words font-mono text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}
