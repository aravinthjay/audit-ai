"use client";

import { ExternalLink, FileSearch, Play } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AuditTimeline } from "@/components/audit/audit-timeline";
import { EvidenceVerificationCard } from "@/components/evidence/evidence-verification-card";
import { DebateMessage } from "@/components/debate/debate-message";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { ReportPreview } from "@/components/reports/report-preview";
import { ChartSkeleton } from "@/components/shared/chart-skeleton";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { RiskBadge } from "@/components/shared/risk-badge";
import { WorkflowStatusBadge } from "@/components/shared/status-badge";
import { VerificationClaimCard } from "@/components/verification/verification-claim-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { routes } from "@/constants/routes";
import { useAgentWorkflow } from "@/hooks/use-agent-workflow";
import { useAuditEvents } from "@/hooks/use-audit-events";
import { useExecuteInvestigation } from "@/hooks/use-cases";
import { useDebateArguments } from "@/hooks/use-debate";
import { useEvidence } from "@/hooks/use-evidence";
import { useEvidenceVerification, useVerifyEvidence } from "@/hooks/use-evidence-verification";
import { useInvestigation } from "@/hooks/use-investigation";
import { useInvestigationRealtime } from "@/hooks/use-investigation-realtime";
import { useReports } from "@/hooks/use-reports";
import { useVerificationClaims } from "@/hooks/use-verification";
import { formatCurrency } from "@/lib/utils";
import type { AgentRole, Investigation, InvestigationStatus, PipelineStep, WorkState } from "@/types/domain";

const AgentWorkflow = dynamic(
  () => import("@/components/agents/agent-workflow").then((m) => m.AgentWorkflow),
  { ssr: false, loading: () => <ChartSkeleton className="h-[520px]" /> },
);

const statusOrder: InvestigationStatus[] = [
  "intake",
  "collecting_evidence",
  "agent_debate",
  "verification",
  "human_review",
  "report_ready",
  "closed",
];

function stageState(current: InvestigationStatus, stage: InvestigationStatus): WorkState {
  if (current === "failed") {
    return stage === "intake" ? "failed" : "idle";
  }

  const currentIndex = statusOrder.indexOf(current);
  const stageIndex = statusOrder.indexOf(stage);

  if (currentIndex < 0 || stageIndex < 0) {
    return "idle";
  }
  if (stageIndex < currentIndex || current === "closed") {
    return "done";
  }
  if (stageIndex === currentIndex) {
    return current === "report_ready" ? "done" : "running";
  }

  return "idle";
}

function workflowFromInvestigation(investigation: Investigation): PipelineStep[] {
  const stages: Array<{
    id: string;
    role: AgentRole | "Report" | "Audit log";
    status: InvestigationStatus;
    detail: string;
    expandedDetail: string;
  }> = [
    {
      id: "intake",
      role: "Supervisor",
      status: "intake",
      detail: `Case ${investigation.transactionId} is registered for ${investigation.vendor}.`,
      expandedDetail: investigation.description,
    },
    {
      id: "evidence",
      role: "Evidence agent",
      status: "collecting_evidence",
      detail: "Collect ledger evidence and deterministic intake rule context.",
      expandedDetail: "Evidence appears after the backend execution endpoint runs for this case.",
    },
    {
      id: "challenger",
      role: "Challenger",
      status: "agent_debate",
      detail: "Challenge the transaction against risk and materiality signals.",
      expandedDetail: "Debate messages are loaded from the backend transcript table.",
    },
    {
      id: "defender",
      role: "Defender",
      status: "agent_debate",
      detail: "Record mitigating arguments and evidence limitations.",
      expandedDetail: "Defender messages are loaded from the backend transcript table.",
    },
    {
      id: "adjudicator",
      role: "Adjudicator",
      status: "agent_debate",
      detail: `Current risk: ${investigation.risk}; confidence ${Math.round(investigation.confidence * 100)}%.`,
      expandedDetail: "Risk and confidence are read from the investigation record.",
    },
    {
      id: "verifier",
      role: "Verifier",
      status: "verification",
      detail: "Verify claims against available evidence.",
      expandedDetail: "Verification claims are loaded from the backend verification table.",
    },
    {
      id: "review",
      role: "Human review",
      status: "human_review",
      detail: investigation.reviewer ? `Assigned to ${investigation.reviewer}.` : "Awaiting reviewer assignment when required.",
      expandedDetail: "Human review status is read from the investigation and review queue APIs.",
    },
    {
      id: "report",
      role: "Report",
      status: "report_ready",
      detail: "Prepare final report package.",
      expandedDetail: "Report artifacts will render here when exposed by the backend API.",
    },
    {
      id: "audit",
      role: "Audit log",
      status: "report_ready",
      detail: "Persist immutable audit events.",
      expandedDetail: "Audit events are loaded from EventStoreDB or the PostgreSQL fallback.",
    },
  ];

  return stages.map((stage) => ({
    id: stage.id,
    role: stage.role,
    state: stageState(investigation.status, stage.status),
    detail: stage.detail,
    latency: undefined,
    confidence: stage.id === "adjudicator" ? investigation.confidence : undefined,
    tokenUsage: 0,
    cost: 0,
    attempt: 1,
    expandedDetail: stage.expandedDetail,
  }));
}

function InlineEmpty({ title, description, icon: Icon = FileSearch }: { title: string; description: string; icon?: typeof FileSearch }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-muted/30 p-6 text-center">
      <Icon className="mx-auto h-6 w-6 text-muted-foreground" aria-hidden="true" />
      <h3 className="mt-3 text-sm font-semibold text-foreground">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

export function CaseWorkspaceView({ caseId }: { caseId: string }) {
  const investigationQuery = useInvestigation(caseId);
  const workflowQuery = useAgentWorkflow(caseId);
  const evidenceQuery = useEvidence(caseId);
  const evidenceVerificationQuery = useEvidenceVerification(caseId);
  const debateQuery = useDebateArguments(caseId);
  const verificationQuery = useVerificationClaims(caseId);
  const reportsQuery = useReports();
  const auditQuery = useAuditEvents(caseId);
  const executeCase = useExecuteInvestigation();
  const verifyEvidence = useVerifyEvidence(caseId);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const { refetch: refetchInvestigation } = investigationQuery;
  const { refetch: refetchEvidence } = evidenceQuery;
  const { refetch: refetchEvidenceVerification } = evidenceVerificationQuery;
  const { refetch: refetchDebate } = debateQuery;
  const { refetch: refetchVerification } = verificationQuery;
  const { refetch: refetchAudit } = auditQuery;

  const investigation = investigationQuery.data;
  const evidence = evidenceQuery.data ?? [];
  const evidenceVerification = evidenceVerificationQuery.data ?? null;
  const debate = debateQuery.data ?? [];
  const verification = verificationQuery.data ?? [];
  const reports = reportsQuery.data ?? [];
  const auditEvents = auditQuery.data ?? [];
  const isPipelineRunning =
    executeCase.isPending ||
    investigation?.status === "collecting_evidence" ||
    investigation?.status === "agent_debate" ||
    investigation?.status === "verification";
  useInvestigationRealtime(caseId, { onMessage: setRunMessage });
  const workflowSteps = useMemo(() => {
    if (!investigation) {
      return [];
    }

    return workflowQuery.data?.length ? workflowQuery.data : workflowFromInvestigation(investigation);
  }, [investigation, workflowQuery.data]);

  const refreshWorkspace = useCallback(async () => {
    await Promise.all([
      refetchInvestigation(),
      refetchEvidence(),
      refetchEvidenceVerification(),
      refetchDebate(),
      refetchVerification(),
      refetchAudit(),
    ]);
  }, [
    refetchAudit,
    refetchDebate,
    refetchEvidence,
    refetchEvidenceVerification,
    refetchInvestigation,
    refetchVerification,
  ]);

  async function handleRunCrew() {
    setRunError(null);
    setRunMessage("Starting the agent crew for this investigation...");

    try {
      const response = await executeCase.mutateAsync(caseId);
      setRunMessage(response.message);
      await refreshWorkspace();
    } catch (error) {
      setRunMessage(null);
      setRunError(error instanceof Error ? error.message : "Unable to start the agent crew.");
    }
  }

  async function handleReverifyEvidence() {
    setRunError(null);
    setRunMessage("Running third-party evidence verification...");

    try {
      const response = await verifyEvidence.mutateAsync(undefined);
      setRunMessage(`Evidence verification completed: ${response.verificationStatus}.`);
      await refreshWorkspace();
    } catch (error) {
      setRunMessage(null);
      setRunError(error instanceof Error ? error.message : "Unable to run evidence verification.");
    }
  }

  useEffect(() => {
    if (!isPipelineRunning) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      void refreshWorkspace();
    }, 1500);

    return () => window.clearInterval(interval);
  }, [isPipelineRunning, refreshWorkspace]);

  if (investigationQuery.isLoading || evidenceQuery.isLoading) {
    return <LoadingState label="Loading case workspace" />;
  }

  if (investigationQuery.error || evidenceQuery.error) {
    return <ErrorState onRetry={() => void Promise.all([investigationQuery.refetch(), evidenceQuery.refetch()])} />;
  }

  if (!investigation) {
    return (
      <EmptyState
        title="Case not found"
        description="The selected investigation does not exist in the current engagement workspace."
        icon={FileSearch}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Investigation workspace"
        title={`${investigation.id} / ${investigation.vendor}`}
        description={investigation.description}
        actions={
          <>
            <Button
              variant={investigation.status === "intake" || investigation.status === "failed" ? "default" : "secondary"}
              disabled={isPipelineRunning}
              onClick={() => void handleRunCrew()}
            >
              <Play className="h-4 w-4" aria-hidden="true" />
              {executeCase.isPending ? "Starting..." : isPipelineRunning ? "Crew running..." : investigation.status === "intake" ? "Run crew" : "Re-run crew"}
            </Button>
            <Button asChild variant="secondary">
              <Link href={routes.replayFor(caseId)}>
                <Play className="h-4 w-4" aria-hidden="true" />
                Replay
              </Link>
            </Button>
            <Button asChild variant="secondary">
              <Link href={routes.evidenceFor(caseId)}>
                <FileSearch className="h-4 w-4" aria-hidden="true" />
                Evidence
              </Link>
            </Button>
            <Button asChild>
              <Link href={routes.review}>
                <ExternalLink className="h-4 w-4" aria-hidden="true" />
                Review
              </Link>
            </Button>
          </>
        }
      />

      {runError ? (
        <div className="rounded-md border border-danger-border bg-danger-soft px-4 py-3 text-sm text-danger-foreground">
          {runError}
        </div>
      ) : runMessage || isPipelineRunning ? (
        <div className="rounded-md border border-info-border bg-info-soft px-4 py-3 text-sm text-info-foreground">
          {runMessage ?? "Agent crew is running. Workspace data will refresh automatically."}
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Agent workflow</CardTitle>
          </CardHeader>
          <CardContent>
            <AgentWorkflow steps={workflowSteps} />
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Case facts</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">Risk</span>
                <RiskBadge risk={investigation.risk} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">Status</span>
                <WorkflowStatusBadge status={investigation.status} />
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">Amount</span>
                <span className="font-mono text-foreground">{formatCurrency(investigation.amount)}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">Materiality</span>
                <span className="font-mono text-foreground">{formatCurrency(investigation.materiality)}</span>
              </div>
              <ConfidenceMeter value={investigation.confidence} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Open flags</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {investigation.flags.length > 0 ? (
                investigation.flags.map((flag) => (
                  <div key={flag} className="rounded-md border border-border bg-background px-3 py-2 text-sm text-muted-foreground">
                    {flag}
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No open flags are recorded for this investigation.</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Human review status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm text-muted-foreground">Reviewer</span>
                <span className="text-sm font-medium text-foreground">{investigation.reviewer ?? "Unassigned"}</span>
              </div>
              <div className="rounded-md border border-warning-border bg-warning-soft px-3 py-2 text-sm text-warning-foreground">
                Awaiting partner decision and digital signature.
              </div>
              <Button asChild variant="secondary" className="w-full">
                <Link href={routes.review}>Open review bundle</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="space-y-3">
        <EvidenceVerificationCard
          error={evidenceVerificationQuery.error}
          isLoading={evidenceVerificationQuery.isLoading}
          isReverifying={verifyEvidence.isPending}
          onReverify={() => void handleReverifyEvidence()}
          verification={evidenceVerification}
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-foreground">Evidence attached to this case</h2>
        {evidence.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {evidence.map((item) => (
              <EvidenceCard key={item.id} evidence={item} />
            ))}
          </div>
        ) : (
          <InlineEmpty
            title={isPipelineRunning ? "Evidence collection is running" : "No evidence collected yet"}
            description={
              isPipelineRunning
                ? "The backend crew has started and this panel will refresh as evidence is persisted."
                : "Run the crew for this case to collect ledger evidence and rule context."
            }
          />
        )}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-foreground">Debate panel</h2>
          <div className="space-y-3">
            {debate.length > 0 ? (
              debate.slice(0, 2).map((argument) => <DebateMessage key={argument.id} argument={argument} />)
            ) : (
              <InlineEmpty
                title={isPipelineRunning ? "Debate is being prepared" : "No debate transcript yet"}
                description={
                  isPipelineRunning
                    ? "Challenger and defender messages will appear after the backend records them."
                    : "Run the crew to create challenger and defender transcript entries."
                }
              />
            )}
            <Button asChild variant="ghost" size="sm">
              <Link href={routes.debateFor(caseId)}>Open full debate</Link>
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <h2 className="text-base font-semibold text-foreground">Verification panel</h2>
          <div className="space-y-3">
            {verification.length > 0 ? (
              verification.slice(0, 2).map((claim) => <VerificationClaimCard key={claim.id} claim={claim} />)
            ) : (
              <InlineEmpty
                title={isPipelineRunning ? "Verification is pending" : "No verification claims yet"}
                description={
                  isPipelineRunning
                    ? "Claim verification will appear when the verifier phase completes."
                    : "Run the crew to verify the generated risk assessment."
                }
              />
            )}
            <Button asChild variant="ghost" size="sm">
              <Link href={routes.verificationFor(caseId)}>Open verifier</Link>
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-foreground">Report preview</h2>
          {reports[0] ? (
            <ReportPreview report={reports[0]} />
          ) : (
            <InlineEmpty
              title="No report artifact yet"
              description="A report preview will appear here when the report API exposes generated artifacts."
            />
          )}
        </div>
        <div className="space-y-3">
          <h2 className="text-base font-semibold text-foreground">Audit trail</h2>
          {auditEvents.length > 0 ? (
            <AuditTimeline events={auditEvents.slice(0, 3)} />
          ) : (
            <InlineEmpty
              title="No audit events recorded yet"
              description="Creating or running the investigation records immutable audit events in PostgreSQL fallback or EventStoreDB."
            />
          )}
        </div>
      </section>
    </div>
  );
}
