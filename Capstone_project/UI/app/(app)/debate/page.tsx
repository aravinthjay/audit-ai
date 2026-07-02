import { DebateView } from "@/features/debate/debate-view";

export default async function DebatePage({
  searchParams,
}: {
  searchParams?: Promise<{
    caseId?: string;
  }>;
}) {
  const { caseId } = (await searchParams) ?? {};

  return <DebateView caseId={caseId} />;
}
