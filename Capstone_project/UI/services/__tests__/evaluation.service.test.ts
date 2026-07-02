import { describe, expect, it } from "vitest";
import { getEvaluationSummary } from "@/services/evaluation.service";

describe("evaluation service", () => {
  it("starts without preloaded RAGAS evaluation results", async () => {
    const summary = await getEvaluationSummary();

    expect(summary.cases).toBe(0);
    expect(summary.metrics).toEqual([]);
    expect(summary.conclusion).toBe("");
  });
});
