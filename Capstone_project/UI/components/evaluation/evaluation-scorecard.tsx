import { CheckCircle2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { RagasCategory, RagasMetric } from "@/types/domain";

type EvaluationScorecardProps = {
  metrics: RagasMetric[];
};

const CATEGORY_META: Record<RagasCategory, { title: string; description: string }> = {
  retrieval: {
    title: "Retrieval quality",
    description: "How well the Evidence agent retrieves relevant, complete policy context.",
  },
  generation: {
    title: "Generation quality",
    description: "How faithful, relevant, and correct the adjudicated verdict is.",
  },
  agentic: {
    title: "Agentic quality",
    description: "How well the crew uses tools, stays on topic, and reaches the goal.",
  },
};

const CATEGORY_ORDER: RagasCategory[] = ["retrieval", "generation", "agentic"];

function formatScore(score: number): string {
  return score.toFixed(2);
}

export function EvaluationScorecard({ metrics }: EvaluationScorecardProps) {
  const groups = CATEGORY_ORDER.map((category) => ({
    category,
    items: metrics.filter((metric) => metric.category === category),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {groups.map(({ category, items }) => {
        const meta = CATEGORY_META[category];

        return (
          <Card key={category}>
            <CardHeader>
              <CardTitle>{meta.title}</CardTitle>
              <p className="text-xs text-muted-foreground">{meta.description}</p>
            </CardHeader>
            <CardContent className="space-y-4">
              {items.map((metric) => (
                <div key={metric.metric} className="space-y-1">
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <span className="flex items-center gap-1.5 text-foreground">
                      {metric.pass ? (
                        <CheckCircle2
                          className="h-3.5 w-3.5 text-success-foreground"
                          aria-hidden="true"
                        />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
                      )}
                      {metric.metric}
                    </span>
                    <span className="font-mono text-foreground">
                      {formatScore(metric.score)}
                      <span className="text-muted-foreground"> / {formatScore(metric.target)}</span>
                    </span>
                  </div>
                  <Progress value={metric.score} tone={metric.pass ? "success" : "danger"} />
                  <p className="text-xs text-muted-foreground">{metric.helper}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
