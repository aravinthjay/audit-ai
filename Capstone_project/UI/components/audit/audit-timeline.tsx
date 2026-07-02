import { Hash } from "lucide-react";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import type { AuditEvent } from "@/types/domain";

export function AuditTimeline({ events }: { events: AuditEvent[] }) {
  return (
    <div className="space-y-3">
      {events.map((event, index) => (
        <Card key={event.id}>
          <CardContent className="p-4">
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <span className="flex h-8 w-8 items-center justify-center rounded-full border border-primary-border bg-primary-soft font-mono text-xs text-primary">
                  {index + 1}
                </span>
                {index < events.length - 1 ? <span className="mt-2 h-full min-h-10 w-px bg-border" /> : null}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="break-words text-sm font-semibold text-foreground">{event.title}</h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {event.timestamp} / {event.actor}
                    </p>
                  </div>
                  <StatusBadge state={event.state} />
                </div>
                <p className="mt-3 break-words text-sm leading-6 text-muted-foreground">{event.detail}</p>
                <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-3">
                  <div className="min-w-0 rounded-md border border-border bg-muted/40 px-3 py-2">
                    Type <span className="break-all font-mono text-foreground">{event.eventType}</span>
                  </div>
                  <div className="min-w-0 rounded-md border border-border bg-muted/40 px-3 py-2">
                    Case <span className="break-all font-mono text-foreground">{event.caseId}</span>
                  </div>
                  <div className="min-w-0 rounded-md border border-border bg-muted/40 px-3 py-2">
                    Source <span className="break-all font-mono text-foreground">{event.sourceRef}</span>
                  </div>
                </div>
                <div className="mt-3 flex min-w-0 items-center gap-2 font-mono text-xs text-muted-foreground">
                  <Hash className="h-3.5 w-3.5" aria-hidden="true" />
                  <span className="break-all">{event.hash}</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
