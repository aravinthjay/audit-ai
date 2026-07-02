import { AuditLogsView } from "@/features/audit/audit-logs-view";

export default async function AuditLogsPage({
  searchParams,
}: {
  searchParams?: Promise<{
    caseId?: string;
  }>;
}) {
  const { caseId } = (await searchParams) ?? {};

  return <AuditLogsView caseId={caseId} />;
}
