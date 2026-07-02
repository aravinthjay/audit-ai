import { ReplayView } from "@/features/replay/replay-view";

export default async function ReplayPage({
  searchParams,
}: {
  searchParams?: Promise<{
    caseId?: string;
  }>;
}) {
  const { caseId } = (await searchParams) ?? {};

  return <ReplayView caseId={caseId} />;
}
