"use client";

import { Download, FileText, Printer } from "lucide-react";
import Link from "next/link";
import { ReportPreview } from "@/components/reports/report-preview";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { routes } from "@/constants/routes";
import { useActiveInvestigationId } from "@/hooks/use-active-investigation-id";
import { useReports } from "@/hooks/use-reports";

export function ReportsView({ caseId: explicitCaseId }: { caseId?: string }) {
  const activeCase = useActiveInvestigationId(explicitCaseId);
  const caseId = activeCase.caseId;
  const { data, error, isLoading, refetch } = useReports();
  const workspaceHref = caseId ? routes.caseWorkspace(caseId) : routes.investigations;

  if (activeCase.isLoading || isLoading) {
    return <LoadingState label="Loading reports" />;
  }

  if (activeCase.error) {
    return <ErrorState onRetry={() => void activeCase.refetch()} />;
  }

  if (error || !data) {
    return <ErrorState onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Report generation"
        title="Professional skepticism reports"
        description="Generate source-grounded memos and governance packs from verified claims, debate outcomes, reviewer decisions, and audit log evidence."
        actions={
          <>
            <Button asChild variant="secondary">
              <Link href={workspaceHref}>
                <FileText className="h-4 w-4" aria-hidden="true" />
                {caseId ? "Open active case" : "Open investigations"}
              </Link>
            </Button>
            <Button variant="secondary">
              <Printer className="h-4 w-4" aria-hidden="true" />
              Print preview
            </Button>
            <Button>
              <Download className="h-4 w-4" aria-hidden="true" />
              Export PDF
            </Button>
          </>
        }
      />

      <section className="grid gap-4">
        {data.map((report) => (
          <ReportPreview key={report.id} report={report} />
        ))}
      </section>

      {data.length === 0 ? (
        <EmptyState
          title="No reports generated"
          description="Reports will appear after the backend exposes report artifacts for verified investigations."
          icon={FileText}
        />
      ) : null}
    </div>
  );
}
