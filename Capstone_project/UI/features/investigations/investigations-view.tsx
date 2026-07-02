"use client";

import { Filter, Plus } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { InvestigationsTable } from "@/components/investigations/investigations-table";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { routes } from "@/constants/routes";
import { useInvestigations } from "@/hooks/use-cases";
import type { Investigation, InvestigationStatus, RiskLevel } from "@/types/domain";

const pageSize = 3;
const emptyInvestigations: Investigation[] = [];

export function InvestigationsView() {
  const { data, error, isLoading, refetch } = useInvestigations();
  const [query, setQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState<RiskLevel | "all">("all");
  const [statusFilter, setStatusFilter] = useState<InvestigationStatus | "all">("all");
  const [dateFrom, setDateFrom] = useState("");
  const [page, setPage] = useState(1);
  const investigations = data ?? emptyInvestigations;
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return investigations.filter((item) => {
      const matchesQuery =
        !normalizedQuery ||
        [item.id, item.vendor, item.category, item.transactionId, item.owner].some((value) =>
          value.toLowerCase().includes(normalizedQuery),
        );
      const matchesRisk = riskFilter === "all" || item.risk === riskFilter;
      const matchesStatus = statusFilter === "all" || item.status === statusFilter;
      const matchesDate = !dateFrom || item.postedAt >= dateFrom;

      return matchesQuery && matchesRisk && matchesStatus && matchesDate;
    });
  }, [dateFrom, investigations, query, riskFilter, statusFilter]);

  if (isLoading) {
    return <LoadingState label="Loading investigations" />;
  }

  if (error || !data) {
    return <ErrorState onRetry={() => void refetch()} />;
  }

  const highRiskCount = investigations.filter((item) => item.risk === "critical" || item.risk === "high").length;
  const reviewCount = investigations.filter((item) => item.status === "human_review").length;
  const firstInvestigationHref = investigations[0] ? routes.caseWorkspace(investigations[0].id) : routes.investigations;
  const pageCount = Math.max(Math.ceil(filtered.length / pageSize), 1);
  const currentPage = Math.min(page, pageCount);
  const paginated = filtered.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Case inventory"
        title="Investigations"
        description="Prioritize exceptions by risk, confidence, materiality, status, reviewer ownership, and open evidence gaps."
        actions={
          <>
            <Button
              variant="secondary"
              onClick={() => {
                setQuery("");
                setRiskFilter("all");
                setStatusFilter("all");
                setDateFrom("");
                setPage(1);
              }}
            >
              <Filter className="h-4 w-4" aria-hidden="true" />
              Clear filters
            </Button>
            <Button asChild>
              <Link href={firstInvestigationHref}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                Open case workspace
              </Link>
            </Button>
          </>
        }
      />

      <section className="grid gap-4 md:grid-cols-3" aria-label="Investigation summary">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Total cases</p>
            <p className="mt-2 font-mono text-2xl text-foreground">{investigations.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Critical or high</p>
            <p className="mt-2 font-mono text-2xl text-danger-foreground">{highRiskCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Human review</p>
            <p className="mt-2 font-mono text-2xl text-warning-foreground">{reviewCount}</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-3 rounded-lg border border-border bg-card p-4 md:grid-cols-4" aria-label="Investigation filters">
        <div className="md:col-span-2">
          <label htmlFor="case-search" className="sr-only">
            Search investigations
          </label>
          <Input
            id="case-search"
            placeholder="Search case, vendor, transaction, or owner"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
          />
        </div>
        <label className="text-xs text-muted-foreground">
          Risk
          <select
            className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
            value={riskFilter}
            onChange={(event) => {
              setRiskFilter(event.target.value as RiskLevel | "all");
              setPage(1);
            }}
          >
            <option value="all">All risks</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="cleared">Cleared</option>
          </select>
        </label>
        <label className="text-xs text-muted-foreground">
          Status
          <select
            className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value as InvestigationStatus | "all");
              setPage(1);
            }}
          >
            <option value="all">All statuses</option>
            <option value="collecting_evidence">Collecting evidence</option>
            <option value="agent_debate">Agent debate</option>
            <option value="verification">Verification</option>
            <option value="human_review">Human review</option>
            <option value="closed">Closed</option>
          </select>
        </label>
        <label className="text-xs text-muted-foreground md:col-span-2">
          Posted after
          <Input
            className="mt-1"
            type="date"
            value={dateFrom}
            onChange={(event) => {
              setDateFrom(event.target.value);
              setPage(1);
            }}
          />
        </label>
        <div className="flex items-end text-xs text-muted-foreground md:col-span-2">
          Showing {paginated.length} of {filtered.length} investigations
        </div>
      </section>

      <InvestigationsTable investigations={paginated} />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted-foreground">
          Page {currentPage} of {pageCount}
        </p>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={currentPage === 1} onClick={() => setPage((value) => Math.max(value - 1, 1))}>
            Previous
          </Button>
          <Button
            variant="secondary"
            disabled={currentPage === pageCount}
            onClick={() => setPage((value) => Math.min(value + 1, pageCount))}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
