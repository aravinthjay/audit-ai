"use client";

import { useQuery } from "@tanstack/react-query";
import { getAuditEvents } from "@/services/audit.service";

export function useAuditEvents(caseId?: string, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["audit-events", caseId ?? "all"],
    queryFn: () => getAuditEvents(caseId),
    enabled: options.enabled ?? true,
  });
}
