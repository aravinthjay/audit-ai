"use client";

import { Gavel, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { DebateMessage } from "@/components/debate/debate-message";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { routes } from "@/constants/routes";
import { useDebatedInvestigations } from "@/hooks/use-cases";
import { useDebateArguments } from "@/hooks/use-debate";
import { useInvestigation } from "@/hooks/use-investigation";
import type { RiskLevel } from "@/types/domain";

const riskVariant: Record<RiskLevel, "danger" | "warning" | "success" | "info"> = {
  critical: "danger",
  high: "danger",
  medium: "warning",
  low: "success",
  cleared: "info",
};

function formatAmount(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

export function DebateView({ caseId: explicitCaseId }: { caseId?: string }) {
  const casesQuery = useDebatedInvestigations({ enabled: !explicitCaseId });
  const cases = casesQuery.data ?? [];
  const [selectedId, setSelectedId] = useState<string>("");
  const caseId = explicitCaseId ?? (selectedId || cases[0]?.id);

  const caseQuery = useInvestigation(caseId, { enabled: Boolean(caseId) });
  const { data, error, isLoading, refetch } = useDebateArguments(caseId, {
    enabled: Boolean(caseId),
  });

  const activeCase = caseQuery.data;

  if ((!explicitCaseId && casesQuery.isLoading) || (caseId && isLoading)) {
    return <LoadingState label="Loading debate" />;
  }

  if (!explicitCaseId && casesQuery.error) {
    return <ErrorState onRetry={() => void casesQuery.refetch()} />;
  }

  const selector =
    !explicitCaseId && cases.length > 0 ? (
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="shrink-0">Case</span>
        <select
          className="h-9 w-72 max-w-[60vw] rounded-md border border-input bg-background px-3 text-sm text-foreground"
          value={caseId ?? ""}
          onChange={(event) => setSelectedId(event.target.value)}
        >
          {cases.map((item) => (
            <option key={item.id} value={item.id}>
              {item.transactionId} — {item.vendor} ({item.risk})
            </option>
          ))}
        </select>
      </label>
    ) : null;

  const header = (
    <PageHeader
      eyebrow="AI debate"
      title="Both sides of the argument"
      description="Two AI helpers argue it out - one looks for problems, the other defends the transaction. See what each said and what stayed unresolved."
      actions={
        <>
          {selector}
          {caseId ? (
            <Button asChild variant="secondary">
              <Link href={routes.caseWorkspace(caseId)}>
                <MessagesSquare className="h-4 w-4" aria-hidden="true" />
                Open workspace
              </Link>
            </Button>
          ) : null}
        </>
      }
    />
  );

  if (!caseId) {
    return (
      <div className="space-y-6">
        {header}
        <EmptyState
          title="No debated cases yet"
          description="Run an investigation from the case workspace to generate a Challenger / Defender debate."
          icon={MessagesSquare}
        />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        {header}
        <ErrorState onRetry={() => void refetch()} />
      </div>
    );
  }

  const challengerArguments = data.filter((argument) => argument.side === "challenger");
  const defenderArguments = data.filter((argument) => argument.side === "defender");
  const adjudicatorArguments = data.filter((argument) => argument.side === "adjudicator");
  const verdict = adjudicatorArguments.at(-1);

  return (
    <div className="space-y-6">
      {header}

      {activeCase ? (
        <Card>
          <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-3 p-4">
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Case</p>
              <p className="truncate text-sm font-semibold text-foreground">
                {activeCase.vendor}
              </p>
              <p className="text-xs text-muted-foreground">
                {activeCase.transactionId} · {activeCase.category}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Amount</p>
              <p className="mt-1 font-mono text-sm text-foreground">
                {formatAmount(activeCase.amount)}
              </p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Risk</p>
              <Badge variant={riskVariant[activeCase.risk]} className="mt-1">
                {activeCase.risk}
              </Badge>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Status</p>
              <p className="mt-1 text-sm text-foreground">{activeCase.status.replaceAll("_", " ")}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Owner</p>
              <p className="mt-1 text-sm text-foreground">{activeCase.owner}</p>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {data.length === 0 ? (
        <EmptyState
          title="No debate messages"
          description="Debate messages will appear after the investigation agent workflow records transcript rounds for this case."
          icon={MessagesSquare}
        />
      ) : (
        <>
          {verdict ? (
            <Card className="border-l-4 border-l-primary">
              <CardContent className="p-4">
                <div className="flex items-center gap-2">
                  <Gavel className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h2 className="text-sm font-semibold text-foreground">Adjudicator verdict</h2>
                  <Badge variant="primary">{verdict.title}</Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{verdict.summary}</p>
                {typeof verdict.confidence === "number" ? (
                  <ConfidenceMeter
                    value={verdict.confidence}
                    label="Verdict confidence"
                    className="mt-4 max-w-sm"
                  />
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-danger-foreground">
                Challenger view
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  worst-case risk
                </span>
              </h2>
              {challengerArguments.length > 0 ? (
                challengerArguments.map((argument) => (
                  <DebateMessage key={argument.id} argument={argument} />
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No challenger arguments recorded.</p>
              )}
            </div>
            <div className="space-y-4">
              <h2 className="text-sm font-semibold text-success-foreground">
                Defender view
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  legitimate rationale
                </span>
              </h2>
              {defenderArguments.length > 0 ? (
                defenderArguments.map((argument) => (
                  <DebateMessage key={argument.id} argument={argument} />
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No defender arguments recorded.</p>
              )}
            </div>
          </section>

          <Card>
            <CardContent className="p-4">
              <details>
                <summary className="cursor-pointer text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  Full debate transcript ({data.length} entries)
                </summary>
                <div className="mt-4 space-y-2">
                  {data.map((argument) => (
                    <div
                      key={`${argument.id}-transcript`}
                      className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm"
                    >
                      <span className="font-medium text-foreground">{argument.side}</span>
                      <span className="mx-2 text-muted-foreground">/</span>
                      <span className="text-muted-foreground">{argument.summary}</span>
                    </div>
                  ))}
                </div>
              </details>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
