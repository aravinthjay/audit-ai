"use client";

import { CheckSquare } from "lucide-react";
import Link from "next/link";
import { VerificationClaimCard } from "@/components/verification/verification-claim-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { routes } from "@/constants/routes";
import { useActiveInvestigationId } from "@/hooks/use-active-investigation-id";
import { useVerificationClaims } from "@/hooks/use-verification";

export function VerificationView({ caseId: explicitCaseId }: { caseId?: string }) {
  const activeCase = useActiveInvestigationId(explicitCaseId);
  const caseId = activeCase.caseId;
  const { data, error, isLoading, refetch } = useVerificationClaims(caseId, { enabled: Boolean(caseId) });

  if (activeCase.isLoading || isLoading) {
    return <LoadingState label="Loading verification claims" />;
  }

  if (activeCase.error) {
    return <ErrorState error={activeCase.error} onRetry={() => void activeCase.refetch()} />;
  }

  if (!caseId) {
    return (
      <EmptyState
        title="No investigation selected"
        description="Create or import an investigation before opening claim verification."
        icon={CheckSquare}
      />
    );
  }

  if (error || !data) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }

  const grounded = data.filter((claim) => claim.status === "grounded").length;
  const unsupported = data.filter((claim) => claim.status === "unsupported").length;
  const missing = data.filter((claim) => claim.status === "missing").length;
  const failed = data.filter((claim) => claim.pass === "failed").length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Fact check"
        title="Is every claim backed up?"
        description="Before a report goes out, we check that each thing the AI says is actually supported by real evidence and up-to-date sources."
        actions={
          <Button asChild>
            <Link href={routes.reportsFor(caseId)}>
              <CheckSquare className="h-4 w-4" aria-hidden="true" />
              Prepare report
            </Link>
          </Button>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Grounded</p>
            <p className="mt-2 font-mono text-2xl text-success-foreground">{grounded}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Unsupported</p>
            <p className="mt-2 font-mono text-2xl text-danger-foreground">{unsupported}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Missing / failed</p>
            <p className="mt-2 font-mono text-2xl text-warning-foreground">{missing + failed}</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        {data.map((claim) => (
          <VerificationClaimCard key={claim.id} claim={claim} />
        ))}
      </section>

      {data.length === 0 ? (
        <EmptyState
          title="No verification claims"
          description="Verification claims will appear after the backend records claim-grounding results."
          icon={CheckSquare}
        />
      ) : null}
    </div>
  );
}
