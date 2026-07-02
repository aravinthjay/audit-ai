"use client";

import { LockKeyhole } from "lucide-react";
import { useEffect, useState } from "react";
import { ReplayControls } from "@/components/replay/replay-controls";
import { EmptyState } from "@/components/shared/empty-state";
import { StatusBadge } from "@/components/shared/status-badge";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useActiveInvestigationId } from "@/hooks/use-active-investigation-id";
import { useReplayFrames } from "@/hooks/use-replay";

export function ReplayView({ caseId: explicitCaseId }: { caseId?: string }) {
  const activeCase = useActiveInvestigationId(explicitCaseId);
  const caseId = activeCase.caseId;
  const { data, error, isLoading, refetch } = useReplayFrames(caseId, { enabled: Boolean(caseId) });
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [activeIndex, setActiveIndex] = useState(0);
  const frames = data ?? [];
  const activeFrame = frames[activeIndex];

  useEffect(() => {
    setActiveIndex((value) => Math.min(value, Math.max(frames.length - 1, 0)));
    if (frames.length === 0) {
      setPlaying(false);
    }
  }, [frames.length]);

  useEffect(() => {
    if (!playing || frames.length <= 1) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setActiveIndex((value) => {
        if (value >= frames.length - 1) {
          setPlaying(false);
          return value;
        }
        return value + 1;
      });
    }, Math.max(350, 1600 / speed));

    return () => window.clearInterval(timer);
  }, [frames.length, playing, speed]);

  function handlePlayingChange(nextPlaying: boolean) {
    if (nextPlaying && activeIndex >= frames.length - 1) {
      setActiveIndex(0);
    }
    setPlaying(nextPlaying);
  }

  if (activeCase.isLoading || isLoading) {
    return <LoadingState label="Loading replay" />;
  }

  if (activeCase.error) {
    return <ErrorState error={activeCase.error} onRetry={() => void activeCase.refetch()} />;
  }

  if (!caseId) {
    return (
      <EmptyState
        title="No investigation selected"
        description="Create or import an investigation before opening the replay timeline."
        icon={LockKeyhole}
      />
    );
  }

  if (error || !data) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }

  if (!activeFrame) {
    return (
      <EmptyState
        title="No replay frames"
        description="This investigation does not have any recorded agent actions yet."
        icon={LockKeyhole}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Investigation replay"
        title={`${caseId} agent playback`}
        description="Step through prompt, input, output, citations, tokens, and cost for each agent action in the immutable investigation sequence."
        actions={
          <Badge variant="primary">
            <LockKeyhole className="mr-1 h-3 w-3" aria-hidden="true" />
            Immutable audit log
          </Badge>
        }
      />

      <ReplayControls
        playing={playing}
        speed={speed}
        onPlayingChange={handlePlayingChange}
        onSpeedChange={setSpeed}
        onStepBack={() => setActiveIndex((value) => Math.max(value - 1, 0))}
        onStepForward={() => setActiveIndex((value) => Math.min(value + 1, frames.length - 1))}
      />

      <section className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <div className="space-y-2">
          {frames.map((frame, index) => (
            <button
              key={frame.id}
              type="button"
              className="w-full rounded-lg border border-border bg-card p-3 text-left hover:bg-muted"
              aria-current={index === activeIndex ? "step" : undefined}
              onClick={() => setActiveIndex(index)}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-foreground">{frame.title}</span>
                <StatusBadge state={frame.state} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {frame.agent} / {frame.timestamp}
              </p>
            </button>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>{activeFrame.title}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 text-xs text-muted-foreground sm:grid-cols-3">
              <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
                Tokens <span className="font-mono text-foreground">{activeFrame.tokenUsage}</span>
              </div>
              <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
                Cost <span className="font-mono text-foreground">${activeFrame.cost.toFixed(2)}</span>
              </div>
              <div className="rounded-md border border-border bg-muted/40 px-3 py-2">
                Speed <span className="font-mono text-foreground">{speed}x</span>
              </div>
            </div>
            {[
              ["Prompt", activeFrame.prompt],
              ["Input", activeFrame.input],
              ["Output", activeFrame.output],
            ].map(([label, value]) => (
              <div key={label}>
                <h2 className="text-sm font-semibold text-foreground">{label}</h2>
                <p className="mt-2 whitespace-pre-wrap break-words rounded-md border border-border bg-background p-3 text-sm leading-6 text-muted-foreground">
                  {value}
                </p>
              </div>
            ))}
            <div>
              <h2 className="text-sm font-semibold text-foreground">Citations</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                {activeFrame.citations.map((citation) => (
                  <Badge key={citation} variant="primary">
                    {citation}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
