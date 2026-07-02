"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { EvidenceVerificationCard } from "@/components/evidence/evidence-verification-card";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { reviewDecisionSchema, type ReviewDecisionForm } from "@/types/forms";
import type {
  DebateArgument,
  EvidenceVerification,
  Investigation,
  ReviewHistoryItem,
  ReviewQueueItem,
} from "@/types/domain";

type HumanReviewPanelProps = {
  investigation?: Investigation;
  evidenceVerification?: EvidenceVerification | null;
  evidenceVerificationError?: unknown;
  evidenceVerificationLoading?: boolean;
  evidenceVerificationReverifying?: boolean;
  queue: ReviewQueueItem[];
  history: ReviewHistoryItem[];
  debate: DebateArgument[];
  onSubmitDecision?: (values: ReviewDecisionForm) => Promise<void>;
  onReverifyEvidence?: () => void;
};

export function HumanReviewPanel({
  investigation,
  evidenceVerification,
  evidenceVerificationError,
  evidenceVerificationLoading,
  evidenceVerificationReverifying,
  queue,
  history,
  debate,
  onSubmitDecision,
  onReverifyEvidence,
}: HumanReviewPanelProps) {
  const [submittedDecision, setSubmittedDecision] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const selectedQueueItem = investigation
    ? queue.find((item) => item.caseId === investigation.id)
    : queue[0];
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<ReviewDecisionForm>({
    resolver: zodResolver(reviewDecisionSchema),
    defaultValues: {
      decision: "request_evidence",
      comment: "",
      signature: "",
    },
  });

  async function onSubmit(values: ReviewDecisionForm) {
    setSubmissionError(null);

    try {
      await onSubmitDecision?.(values);
      setSubmittedDecision(values.decision);
    } catch (error) {
      setSubmittedDecision(null);
      setSubmissionError(error instanceof Error ? error.message : "Unable to submit review decision.");
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
      <Card>
        <CardHeader>
          <CardTitle>Reviewer decision</CardTitle>
        </CardHeader>
        <CardContent>
          {investigation ? (
            <div className="mb-5 rounded-lg border border-border bg-background p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="break-all font-mono text-xs text-primary">{investigation.id}</p>
                  <h2 className="mt-1 text-lg font-semibold text-foreground">{investigation.vendor}</h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{investigation.description}</p>
                </div>
                <RiskBadge risk={investigation.risk} />
              </div>
              {selectedQueueItem ? (
                <div className="mt-4 grid gap-2 rounded-md border border-border bg-muted/30 p-3 text-xs text-muted-foreground sm:grid-cols-3">
                  <div>
                    <span className="block uppercase tracking-[0.08em]">Assigned to</span>
                    <span className="mt-1 block font-medium text-foreground">
                      {selectedQueueItem.assignedTo ?? "Unassigned"}
                    </span>
                  </div>
                  <div>
                    <span className="block uppercase tracking-[0.08em]">Queue</span>
                    <span className="mt-1 block font-medium text-foreground">
                      {selectedQueueItem.queue} / priority {selectedQueueItem.priority}
                    </span>
                  </div>
                  <div>
                    <span className="block uppercase tracking-[0.08em]">Reason</span>
                    <span className="mt-1 block text-foreground">{selectedQueueItem.notes ?? "Awaiting review decision."}</span>
                  </div>
                </div>
              ) : null}
              <ConfidenceMeter value={investigation.confidence} className="mt-4 max-w-sm" />
            </div>
          ) : (
            <div className="mb-5 rounded-lg border border-dashed border-border bg-background p-4 text-sm text-muted-foreground">
              No cases are currently assigned for human review.
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
            <fieldset className="space-y-2" disabled={!investigation || isSubmitting}>
              <legend className="text-sm font-medium text-foreground">Decision</legend>
              <label className="flex items-center gap-3 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
                <input type="radio" value="approve" {...register("decision")} />
                Approve conclusion
              </label>
              <label className="flex items-center gap-3 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
                <input type="radio" value="reject" {...register("decision")} />
                Reject conclusion
              </label>
              <label className="flex items-center gap-3 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
                <input type="radio" value="request_evidence" {...register("decision")} />
                Request additional evidence
              </label>
              <label className="flex items-center gap-3 rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
                <input type="radio" value="escalate" {...register("decision")} />
                Escalate to engagement partner
              </label>
            </fieldset>

            <div>
              <label htmlFor="review-comment" className="text-sm font-medium text-foreground">
                Review rationale
              </label>
              <Textarea
                id="review-comment"
                className="mt-2"
                placeholder="Record the decision rationale for the immutable audit log."
                {...register("comment")}
              />
              {errors.comment ? <p className="mt-2 text-xs text-danger-foreground">{errors.comment.message}</p> : null}
            </div>

            <div>
              <label htmlFor="review-signature" className="text-sm font-medium text-foreground">
                Digital signature
              </label>
              <Input id="review-signature" className="mt-2" placeholder="e.g. p.nair" {...register("signature")} />
              {errors.signature ? <p className="mt-2 text-xs text-danger-foreground">{errors.signature.message}</p> : null}
            </div>

            {submittedDecision ? (
              <p className="rounded-md border border-success-border bg-success-soft px-3 py-2 text-sm text-success-foreground">
                Decision submitted: {submittedDecision.replace("_", " ")}
              </p>
            ) : null}

            {submissionError ? (
              <p className="rounded-md border border-danger-border bg-danger-soft px-3 py-2 text-sm text-danger-foreground">
                {submissionError}
              </p>
            ) : null}

            <Button type="submit" disabled={isSubmitting || !investigation}>
              Submit review decision
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <EvidenceVerificationCard
          error={evidenceVerificationError}
          isLoading={evidenceVerificationLoading}
          isReverifying={evidenceVerificationReverifying}
          onReverify={onReverifyEvidence}
          verification={evidenceVerification}
        />

        <Card>
          <CardHeader>
            <CardTitle>Reviewer and partner queues</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {queue.length === 0 ? (
              <p className="rounded-md border border-dashed border-border bg-background p-3 text-sm text-muted-foreground">
                No reviewer or partner queue items are pending.
              </p>
            ) : null}
            {queue.map((item) => (
              <div
                key={item.id}
                className={`rounded-md border bg-background p-3 ${
                  investigation?.id === item.caseId ? "border-primary/60" : "border-border"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="break-all font-mono text-xs text-primary">{item.caseId}</span>
                  <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">{item.queue}</span>
                  <RiskBadge risk={item.risk} />
                </div>
                <p className="mt-2 text-sm font-medium text-foreground">{item.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Assigned to {item.assignedTo ?? "Unassigned"} / priority {item.priority} / due {item.dueAt}
                </p>
                {item.notes ? <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.notes}</p> : null}
                <ConfidenceMeter value={item.confidence} className="mt-3" />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Review history</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {history.length === 0 ? (
              <p className="rounded-md border border-dashed border-border bg-background p-3 text-sm text-muted-foreground">
                No human review actions have been recorded yet.
              </p>
            ) : null}
            {history.map((item) => (
              <div key={item.id} className="rounded-md border border-border bg-background p-3 text-sm">
                <div className="flex justify-between gap-3">
                  <span className="font-medium text-foreground">{item.actor}</span>
                  <span className="text-xs text-muted-foreground">{item.timestamp}</span>
                </div>
                <p className="mt-1 text-xs uppercase tracking-[0.08em] text-primary">{item.action.replace("_", " ")}</p>
                <p className="mt-2 text-muted-foreground">{item.comment}</p>
                <p className="mt-2 font-mono text-xs text-muted-foreground">signature: {item.signature}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Debate transcript bundle</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {debate.length === 0 ? (
              <p className="rounded-md border border-dashed border-border bg-background p-3 text-sm text-muted-foreground">
                No debate transcript is available for this case yet.
              </p>
            ) : null}
            {debate.slice(0, 3).map((argument) => (
              <div key={argument.id} className="rounded-md border border-border bg-background p-3 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">{argument.side}</span>: {argument.summary}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
