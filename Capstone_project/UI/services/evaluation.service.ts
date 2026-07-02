import { apiRequest } from "@/services/api";
import type { EvaluationSummary, RagasMetric } from "@/types/domain";

type ApiRagasMetric = {
  metric: string;
  category: RagasMetric["category"];
  score: number;
  target: number;
  pass: boolean;
  helper: string;
};

type ApiEvaluationSummary = {
  cases: number;
  metrics: ApiRagasMetric[];
  conclusion: string;
};

export async function getEvaluationSummary(): Promise<EvaluationSummary> {
  const data = await apiRequest<ApiEvaluationSummary>("/evaluation/summary");

  return {
    cases: data.cases,
    metrics: data.metrics.map((metric) => ({
      metric: metric.metric,
      category: metric.category,
      score: metric.score,
      target: metric.target,
      pass: metric.pass,
      helper: metric.helper,
    })),
    conclusion: data.conclusion,
  };
}
