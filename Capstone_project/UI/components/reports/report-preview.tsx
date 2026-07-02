"use client";

import { FileText } from "lucide-react";
import { ConfidenceMeter } from "@/components/shared/confidence-meter";
import { RiskBadge } from "@/components/shared/risk-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { downloadReportJson, downloadReportPdf } from "@/lib/report-export";
import type { ReportArtifact } from "@/types/domain";

const statusTone = {
  draft: "warning",
  ready: "info",
  approved: "success",
} as const;

export function ReportPreview({ report }: { report: ReportArtifact }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-info-border bg-info-soft text-info-foreground">
            <FileText className="h-4 w-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground">{report.title}</h2>
              <Badge variant={statusTone[report.status]}>{report.status}</Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {report.audience} / {report.updatedAt}
            </p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{report.executiveSummary}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <RiskBadge risk={report.riskVerdict} />
              <Badge variant="primary">Decision: {report.humanDecision}</Badge>
              <Badge>Signature: {report.reviewerSignature}</Badge>
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
              {report.sections.map((section) => (
                <div key={section} className="rounded-md border border-border bg-background px-3 py-2 text-xs text-muted-foreground">
                  {section}
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <ConfidenceMeter value={report.confidence} className="w-full sm:max-w-xs" />
              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" onClick={() => downloadReportPdf(report)}>
                  Open report
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const opened = downloadReportPdf(report);
                    if (!opened) {
                      window.alert("Allow pop-ups for this site to save the report as a PDF.");
                    }
                  }}
                >
                  PDF
                </Button>
                <Button variant="ghost" size="sm" onClick={() => downloadReportJson(report)}>
                  JSON
                </Button>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
