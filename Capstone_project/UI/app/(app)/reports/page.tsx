import { ReportsView } from "@/features/reports/reports-view";

export default async function ReportsPage({
  searchParams,
}: {
  searchParams?: Promise<{
    caseId?: string;
  }>;
}) {
  const { caseId } = (await searchParams) ?? {};

  return <ReportsView caseId={caseId} />;
}
