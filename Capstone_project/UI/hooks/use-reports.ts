"use client";

import { useQuery } from "@tanstack/react-query";
import { getReports } from "@/services/reports.service";

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: getReports,
  });
}
