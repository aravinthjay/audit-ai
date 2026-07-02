import { VerificationView } from "@/features/verification/verification-view";

export default async function VerificationPage({
  searchParams,
}: {
  searchParams?: Promise<{
    caseId?: string;
  }>;
}) {
  const { caseId } = (await searchParams) ?? {};

  return <VerificationView caseId={caseId} />;
}
