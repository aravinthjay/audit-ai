import { EvidenceView } from "@/features/evidence/evidence-view";

export default async function EvidencePage({
  searchParams,
}: {
  searchParams?: Promise<{
    caseId?: string;
  }>;
}) {
  const { caseId } = (await searchParams) ?? {};

  return <EvidenceView caseId={caseId} />;
}
