"use client";

import { UserCheck } from "lucide-react";
import Link from "next/link";
import { HumanReviewPanel } from "@/components/review/human-review-panel";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { routes } from "@/constants/routes";
import { useReviewQueue } from "@/hooks/use-cases";
import { useDebateArguments } from "@/hooks/use-debate";
import { useEvidenceVerification, useVerifyEvidence } from "@/hooks/use-evidence-verification";
import { useInvestigation } from "@/hooks/use-investigation";
import { useReviewHistory, useSubmitReviewDecision } from "@/hooks/use-review";
import type { ReviewDecisionForm } from "@/types/forms";

export function HumanReviewView({ caseId }: { caseId?: string }) {
  const queueQuery = useReviewQueue();
  const activeCaseId = caseId ?? queueQuery.data?.[0]?.caseId ?? "";
  const hasActiveCase = activeCaseId.length > 0;
  const investigationQuery = useInvestigation(activeCaseId, { enabled: hasActiveCase });
  const historyQuery = useReviewHistory(activeCaseId, { enabled: hasActiveCase });
  const debateQuery = useDebateArguments(activeCaseId, { enabled: hasActiveCase });
  const evidenceVerificationQuery = useEvidenceVerification(activeCaseId, { enabled: hasActiveCase });
  const submitDecision = useSubmitReviewDecision();
  const verifyEvidence = useVerifyEvidence(activeCaseId);

  async function handleSubmitDecision(values: ReviewDecisionForm) {
    if (!activeCaseId) {
      throw new Error("No review case is selected.");
    }

    await submitDecision.mutateAsync({
      caseId: activeCaseId,
      decision: values.decision,
      comment: values.comment,
      signature: values.signature,
    });
  }

  async function handleReverifyEvidence() {
    if (!activeCaseId) {
      throw new Error("No review case is selected.");
    }

    await verifyEvidence.mutateAsync(undefined);
  }

  if (
    queueQuery.isLoading ||
    (hasActiveCase && (investigationQuery.isLoading || historyQuery.isLoading || debateQuery.isLoading))
  ) {
    return <LoadingState label="Loading review queue" />;
  }

  if (queueQuery.error || (hasActiveCase && (investigationQuery.error || historyQuery.error || debateQuery.error))) {
    return (
      <ErrorState
        onRetry={() =>
          void Promise.all([investigationQuery.refetch(), queueQuery.refetch(), historyQuery.refetch(), debateQuery.refetch()])
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Human review"
        title="Partner decision panel"
        description="Document reviewer judgement, capture rationale, and preserve the decision trail for high-risk AI-assisted conclusions."
        actions={
          <Button asChild variant="secondary">
            <Link href={activeCaseId ? routes.auditLogsFor(activeCaseId) : routes.auditLogs}>
              <UserCheck className="h-4 w-4" aria-hidden="true" />
              View audit trail
            </Link>
          </Button>
        }
      />

      <HumanReviewPanel
        debate={debateQuery.data ?? []}
        history={historyQuery.data ?? []}
        evidenceVerification={evidenceVerificationQuery.data ?? null}
        evidenceVerificationError={evidenceVerificationQuery.error}
        evidenceVerificationLoading={evidenceVerificationQuery.isLoading}
        evidenceVerificationReverifying={verifyEvidence.isPending}
        investigation={investigationQuery.data}
        onSubmitDecision={handleSubmitDecision}
        onReverifyEvidence={() => void handleReverifyEvidence()}
        queue={queueQuery.data ?? []}
      />
    </div>
  );
}
