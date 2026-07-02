"use client";

import { FileSearch } from "lucide-react";
import { useMemo, useState } from "react";
import { EvidenceCard } from "@/components/evidence/evidence-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useActiveInvestigationId } from "@/hooks/use-active-investigation-id";
import { useEvidence } from "@/hooks/use-evidence";
import { useEvidenceVerification } from "@/hooks/use-evidence-verification";
import { useInvestigation } from "@/hooks/use-investigation";
import { evidenceFromVerification } from "@/services/evidence.service";
import { formatCurrency } from "@/lib/utils";
import type { EvidenceSource } from "@/types/domain";

const emptyEvidence: EvidenceSource[] = [];

export function EvidenceView({ caseId: explicitCaseId }: { caseId?: string }) {
  const activeCase = useActiveInvestigationId(explicitCaseId);
  const caseId = activeCase.caseId;
  const { data, error, isLoading, refetch } = useEvidence(caseId, { enabled: Boolean(caseId) });
  const investigationQuery = useInvestigation(caseId, { enabled: Boolean(caseId) });
  const evidenceVerificationQuery = useEvidenceVerification(caseId, { enabled: Boolean(caseId) });
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<EvidenceSource["type"] | "all">("all");
  const [qualityFilter, setQualityFilter] = useState<EvidenceSource["quality"] | "all">("all");
  const investigation = investigationQuery.data;
  const evidence = useMemo(() => {
    const thirdPartyEvidence = evidenceFromVerification(evidenceVerificationQuery.data, caseId ?? "");

    return thirdPartyEvidence ? [...(data ?? emptyEvidence), thirdPartyEvidence] : (data ?? emptyEvidence);
  }, [caseId, data, evidenceVerificationQuery.data]);
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return evidence.filter((item) => {
      const matchesQuery =
        !normalizedQuery ||
        [item.title, item.summary, item.citation, item.type, ...item.tags].some((value) =>
          value.toLowerCase().includes(normalizedQuery),
        );
      const matchesType = typeFilter === "all" || item.type === typeFilter;
      const matchesQuality = qualityFilter === "all" || item.quality === qualityFilter;

      return matchesQuery && matchesType && matchesQuality;
    });
  }, [evidence, qualityFilter, query, typeFilter]);

  if (activeCase.isLoading || isLoading || investigationQuery.isLoading) {
    return <LoadingState label="Loading evidence" />;
  }

  if (activeCase.error) {
    return <ErrorState onRetry={() => void activeCase.refetch()} />;
  }

  if (!caseId) {
    return (
      <EmptyState
        title="No investigation selected"
        description="Create or import an investigation before exploring evidence."
        icon={FileSearch}
      />
    );
  }

  if (error || investigationQuery.error || !data) {
    return <ErrorState onRetry={() => void Promise.all([refetch(), investigationQuery.refetch()])} />;
  }

  const caseTitle = investigation
    ? `${investigation.transactionId} / ${investigation.vendor}`
    : caseId;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Evidence explorer"
        title="Source-grounded evidence"
        description={`Viewing all evidence attached to case ${caseTitle}. Ledger, intake, and third-party provider verification are shown together.`}
        actions={
          <Button variant="secondary">
            <FileSearch className="h-4 w-4" aria-hidden="true" />
            Source map
          </Button>
        }
      />

      <Card>
        <CardContent className="grid gap-4 p-4 md:grid-cols-4">
          <div className="min-w-0 md:col-span-2">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Selected case</p>
            <p className="mt-2 break-words font-mono text-sm font-semibold text-foreground">{caseId}</p>
            <p className="mt-1 text-sm text-muted-foreground">{caseTitle}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Category</p>
            <p className="mt-2 text-sm font-medium text-foreground">{investigation?.category ?? "Unknown"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Amount</p>
            <p className="mt-2 font-mono text-sm font-medium text-foreground">
              {formatCurrency(investigation?.amount ?? 0)}
            </p>
          </div>
        </CardContent>
      </Card>

      {evidenceVerificationQuery.error ? (
        <div className="rounded-md border border-warning-border bg-warning-soft px-4 py-3 text-sm text-warning-foreground">
          Third-party evidence verification could not be loaded for this case. Ledger and intake evidence are still shown.
        </div>
      ) : null}

      <section className="grid gap-3 rounded-lg border border-border bg-card p-4 md:grid-cols-4" aria-label="Evidence filters">
        <div className="md:col-span-2">
          <label htmlFor="evidence-search" className="sr-only">
            Search evidence
          </label>
          <Input
            id="evidence-search"
            placeholder="Search evidence title, citation, or tag"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <label className="text-xs text-muted-foreground">
          Source type
          <select
            className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value as EvidenceSource["type"] | "all")}
          >
            <option value="all">All sources</option>
            <option value="Policy">Policy</option>
            <option value="History">History</option>
            <option value="Vendor">Vendor</option>
            <option value="External API">External API</option>
            <option value="Ledger">Ledger</option>
            <option value="Contract">Contract</option>
          </select>
        </label>
        <label className="text-xs text-muted-foreground">
          Quality
          <select
            className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
            value={qualityFilter}
            onChange={(event) => setQualityFilter(event.target.value as EvidenceSource["quality"] | "all")}
          >
            <option value="all">All quality</option>
            <option value="strong">Strong</option>
            <option value="adequate">Adequate</option>
            <option value="weak">Weak</option>
            <option value="missing">Missing</option>
          </select>
        </label>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        {filtered.map((evidence) => (
          <EvidenceCard key={evidence.id} evidence={evidence} />
        ))}
      </section>

      {filtered.length === 0 ? (
        <EmptyState
          title="No evidence matches"
          description="Adjust the search or filters to inspect other evidence attached to this investigation."
          icon={FileSearch}
        />
      ) : null}
    </div>
  );
}
