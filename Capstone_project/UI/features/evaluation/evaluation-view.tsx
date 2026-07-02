"use client";

import { FileDown, FlaskConical, RefreshCw } from "lucide-react";
import { EvaluationScorecard } from "@/components/evaluation/evaluation-scorecard";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useEvaluationSummary } from "@/hooks/use-evaluation";

export function EvaluationView() {
  const { data, error, isLoading, refetch } = useEvaluationSummary();

  if (isLoading) {
    return <LoadingState label="Loading evaluation" />;
  }

  if (error || !data) {
    return <ErrorState onRetry={() => void refetch()} />;
  }

  const hasEvaluation = data.cases > 0 || data.metrics.length > 0;
  const passing = data.metrics.filter((metric) => metric.pass).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="RAGAS evaluation"
        title="Retrieval, generation & agentic quality"
        description={`Scored over ${data.cases} labelled golden-set cases with RAGAS - faithfulness, context precision/recall, and agent goal accuracy.`}
        actions={
          <>
            <Button variant="secondary">
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Re-run eval
            </Button>
            <Button>
              <FileDown className="h-4 w-4" aria-hidden="true" />
              Export results
            </Button>
          </>
        }
      />

      {hasEvaluation ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  Golden-set cases
                </p>
                <p className="mt-2 font-mono text-2xl text-foreground">{data.cases}</p>
                <p className="mt-1 text-xs text-muted-foreground">Labelled with reference answers</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  Metrics passing
                </p>
                <p className="mt-2 font-mono text-2xl text-foreground">
                  {passing}/{data.metrics.length}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">Meeting their thresholds</p>
              </CardContent>
            </Card>
          </section>

          <EvaluationScorecard metrics={data.metrics} />

          {data.conclusion ? (
            <Card className="border-l-4 border-l-primary">
              <CardContent className="p-4">
                <p className="text-sm font-semibold text-primary">Conclusion</p>
                <p className="mt-1 text-sm text-muted-foreground">{data.conclusion}</p>
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : (
        <EmptyState
          title="No evaluation results"
          description="RAGAS scores will appear after a backend evaluation run is recorded."
          icon={FlaskConical}
        />
      )}
    </div>
  );
}
