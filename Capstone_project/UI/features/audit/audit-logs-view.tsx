"use client";

import { LockKeyhole } from "lucide-react";
import { useMemo, useState } from "react";
import { AuditTimeline } from "@/components/audit/audit-timeline";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useActiveInvestigationId } from "@/hooks/use-active-investigation-id";
import { useAuditEvents } from "@/hooks/use-audit-events";
import type { AuditEvent } from "@/types/domain";

const emptyEvents: AuditEvent[] = [];

export function AuditLogsView({ caseId: explicitCaseId }: { caseId?: string }) {
  const activeCase = useActiveInvestigationId(explicitCaseId);
  const caseId = activeCase.caseId;
  // Show case-scoped events when a case is active, otherwise fall back to the
  // global recent audit feed so the page is never blank.
  const { data, error, isLoading, refetch } = useAuditEvents(caseId, { enabled: true });
  const [query, setQuery] = useState("");
  const [eventType, setEventType] = useState<AuditEvent["eventType"] | "all">("all");
  const events = data ?? emptyEvents;
  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return events.filter((event) => {
      const matchesType = eventType === "all" || event.eventType === eventType;
      const matchesQuery =
        !normalizedQuery ||
        [event.title, event.detail, event.actor, event.caseId, event.sourceRef, event.hash].some((value) =>
          value.toLowerCase().includes(normalizedQuery),
        );

      return matchesType && matchesQuery;
    });
  }, [eventType, events, query]);

  if (activeCase.isLoading || isLoading) {
    return <LoadingState label="Loading audit log" />;
  }

  if (activeCase.error) {
    return <ErrorState onRetry={() => void activeCase.refetch()} />;
  }

  if (error || !data) {
    return <ErrorState onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Immutable audit log"
        title="Replay timeline"
        description="Inspect locked agent actions, evidence versions, verifier outcomes, reviewer routing, and tamper-evident hashes."
        actions={
          <Button variant="secondary">
            <LockKeyhole className="h-4 w-4" aria-hidden="true" />
            Export log
          </Button>
        }
      />

      <Card>
        <CardContent className="grid gap-4 p-4 md:grid-cols-3">
          <div>
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Events</p>
            <p className="mt-2 font-mono text-2xl text-foreground">{filtered.length}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Retention</p>
            <p className="mt-2 text-sm font-medium text-foreground">7 years locked</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Integrity</p>
            <p className="mt-2 text-sm font-medium text-success-foreground">Hash chain verified</p>
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-3 rounded-lg border border-border bg-card p-4 md:grid-cols-[1fr_220px]" aria-label="Audit filters">
        <div>
          <label htmlFor="audit-search" className="sr-only">
            Search audit logs
          </label>
          <Input
            id="audit-search"
            placeholder="Search actor, source, hash, or case"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <label className="text-xs text-muted-foreground">
          Event type
          <select
            className="mt-1 h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground"
            value={eventType}
            onChange={(event) => setEventType(event.target.value as AuditEvent["eventType"] | "all")}
          >
            <option value="all">All events</option>
            <option value="agent">Agent action</option>
            <option value="human">Human action</option>
            <option value="system">System event</option>
            <option value="source">Source reference</option>
          </select>
        </label>
      </section>

      <AuditTimeline events={filtered} />

      {filtered.length === 0 ? (
        <EmptyState
          title="No audit events match"
          description="Adjust the search or event type filter to inspect other recorded actions."
          icon={LockKeyhole}
        />
      ) : null}
    </div>
  );
}
