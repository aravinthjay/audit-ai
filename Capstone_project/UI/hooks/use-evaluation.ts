"use client";

import { useQuery } from "@tanstack/react-query";
import { getEvaluationSummary } from "@/services/evaluation.service";

export function useEvaluationSummary() {
  return useQuery({
    queryKey: ["evaluation-summary"],
    queryFn: getEvaluationSummary,
  });
}
