"use client";

import { useQuery } from "@tanstack/react-query";
import { getIntakeSummary } from "@/services/intake.service";

export function useIntakeSummary() {
  return useQuery({
    queryKey: ["intake-summary"],
    queryFn: getIntakeSummary,
  });
}
