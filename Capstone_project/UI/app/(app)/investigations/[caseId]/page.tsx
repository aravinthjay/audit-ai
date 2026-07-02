import { CaseWorkspaceView } from "@/features/investigations/case-workspace-view";

export default async function CaseWorkspacePage({
  params,
}: {
  params: Promise<{
    caseId: string;
  }>;
}) {
  const { caseId } = await params;

  return <CaseWorkspaceView caseId={caseId} />;
}
