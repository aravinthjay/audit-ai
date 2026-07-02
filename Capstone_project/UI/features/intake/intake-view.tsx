"use client";

import { ArrowRight, FileSpreadsheet, History, Info, Play, Trash2, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { FlaggedRowsTable } from "@/components/intake/flagged-rows-table";
import { RulePrefilter } from "@/components/intake/rule-prefilter";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { LoadingState } from "@/components/shared/loading-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { routes } from "@/constants/routes";
import { heldBackCaseCount, MAX_CASES_PER_INTAKE_RUN, rowsForCaseCreation } from "@/features/intake/intake-limits";
import { useCreateInvestigations, useDeleteImportedInvestigations, useExecuteInvestigations } from "@/hooks/use-cases";
import { useIntakeSummary } from "@/hooks/use-intake";
import { useSettings } from "@/hooks/use-settings";
import { defaultIntakeParseOptions, parseLedgerFile } from "@/services/intake.service";
import type { FlaggedRow, IntakeSummary } from "@/types/domain";

function parseCurrencyAmount(value: string) {
  const parsed = Number(value.replace(/[^0-9.-]/g, ""));

  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0.01;
}

function toInvestigationInput(row: FlaggedRow, summary: IntakeSummary, materiality: number) {
  return {
    transactionId: row.txnId,
    vendor: row.vendor,
    category: row.account,
    amount: parseCurrencyAmount(row.amount),
    materiality,
    owner: "intake",
    description: [
      `Created from intake file ${summary.fileName}.`,
      `Rules fired: ${row.rules.join(", ")}.`,
      `Source account: ${row.account}.`,
    ].join(" "),
  };
}

export function IntakeView() {
  const router = useRouter();
  const { data, error, isLoading, refetch } = useIntakeSummary();
  const settingsQuery = useSettings();
  const createCases = useCreateInvestigations();
  const deleteImportedCases = useDeleteImportedInvestigations();
  const runCases = useExecuteInvestigations();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploadedSummary, setUploadedSummary] = useState<IntakeSummary | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [showPastRuns, setShowPastRuns] = useState(false);
  const [runStatus, setRunStatus] = useState("Upload a CSV or TSV ledger extract to run the pre-filter.");
  const parserOptions = useMemo(
    () => ({
      materialityThreshold: settingsQuery.data?.materiality ?? defaultIntakeParseOptions.materialityThreshold,
      estimatedAgentRunCostUsd:
        settingsQuery.data?.estimatedAgentRunCostUsd ?? defaultIntakeParseOptions.estimatedAgentRunCostUsd,
      displayCurrency: settingsQuery.data?.displayCurrency ?? defaultIntakeParseOptions.displayCurrency,
      segregationOfDutiesTokens: defaultIntakeParseOptions.segregationOfDutiesTokens,
    }),
    [settingsQuery.data],
  );

  async function handleFile(file?: File) {
    if (!file) {
      return;
    }

    if (!/\.(csv|tsv)$/i.test(file.name)) {
      setUploadError("Upload a CSV or TSV ledger extract.");
      return;
    }

    setIsParsing(true);
    setUploadError(null);
    setCreateError(null);

    try {
      const parsed = await parseLedgerFile(file, parserOptions);
      setUploadedSummary(parsed);
      setRunStatus(`Parsed ${parsed.fileName}; ${parsed.flagged} rows flagged for case creation.`);
    } catch (parseError) {
      setUploadError(parseError instanceof Error ? parseError.message : "Unable to parse the uploaded file.");
    } finally {
      setIsParsing(false);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  async function handleDeleteImportedCases() {
    const confirmed = window.confirm(
      "Delete all cases created from intake uploads? This removes their evidence, debate, verification, audit, and review data from the database.",
    );

    if (!confirmed) {
      return;
    }

    setCreateError(null);
    setRunStatus("Deleting imported intake cases from the backend...");

    try {
      const result = await deleteImportedCases.mutateAsync();
      setRunStatus(result.message);
    } catch (deleteError) {
      setCreateError(deleteError instanceof Error ? deleteError.message : "Unable to delete imported intake data.");
      setRunStatus("Imported data deletion failed. Check the backend connection and try again.");
    }
  }

  async function handleCreateCases(summary: IntakeSummary, options: { replaceExisting?: boolean } = {}) {
    const rowsToCreate = rowsForCaseCreation(summary.flaggedRows);
    const skippedRows = heldBackCaseCount(summary.flaggedRows.length);

    if (summary.flaggedRows.length === 0) {
      setRunStatus("No flagged rows are available for case creation.");
      return;
    }

    setCreateError(null);
    setRunStatus(
      options.replaceExisting
        ? "Deleting existing imported cases before replacement..."
        : `Creating ${rowsToCreate.length} cases in the backend...`,
    );

    try {
      if (options.replaceExisting) {
        const confirmed = window.confirm(
          "Replace imported backend data with this upload? Existing intake-created cases and their generated data will be deleted first.",
        );

        if (!confirmed) {
          setRunStatus("Replacement cancelled.");
          return;
        }

        const deleted = await deleteImportedCases.mutateAsync();
        setRunStatus(`${deleted.message} Creating ${rowsToCreate.length} replacement cases...`);
      }

      const created = await createCases.mutateAsync(
        rowsToCreate.map((row) => toInvestigationInput(row, summary, parserOptions.materialityThreshold)),
      );
      const limitMessage = skippedRows > 0 ? ` ${skippedRows} additional flagged row(s) were held for the next run.` : "";
      setRunStatus(`Created ${created.length} cases.${limitMessage} Starting the agent crew...`);
      await runCases.mutateAsync(created.map((item) => item.id));
      setRunStatus(`Started the crew for ${created.length} cases. Opening the first workspace...`);
      router.push(routes.caseWorkspace(created[0].id));
    } catch (creationError) {
      setCreateError(
        creationError instanceof Error
          ? creationError.message
          : "Unable to create cases or start the agent crew in the backend.",
      );
      setRunStatus("Case creation or crew execution failed. Check the backend connection and try again.");
    }
  }

  if (isLoading || settingsQuery.isLoading) {
    return <LoadingState label="Loading intake run" />;
  }

  if (error || settingsQuery.error) {
    return <ErrorState onRetry={() => void Promise.all([refetch(), settingsQuery.refetch()])} />;
  }

  const summary = uploadedSummary ?? data;
  const intakeRuns = uploadedSummary ? [uploadedSummary] : [];
  const stats = summary
    ? [
        {
          label: "Rows ingested",
          value: summary.rowsIngested.toLocaleString(),
          helper: `${summary.parseErrors} parse errors`,
          tone: "text-foreground",
        },
        {
          label: "Flagged -> cases",
          value: Math.min(summary.flagged, MAX_CASES_PER_INTAKE_RUN).toLocaleString(),
          helper:
            summary.flagged > MAX_CASES_PER_INTAKE_RUN
              ? `${summary.flagged - MAX_CASES_PER_INTAKE_RUN} held back`
              : "enter the crew",
          tone: "text-primary",
        },
        {
          label: "Cleared at intake",
          value: summary.cleared.toLocaleString(),
          helper: "dropped - no case",
          tone: "text-success-foreground",
        },
        {
          label: "Est. crew cost",
          value: `$${summary.estCostUsd}`,
          helper: `${summary.flagged} x $${parserOptions.estimatedAgentRunCostUsd.toFixed(2)}`,
          tone: "text-foreground",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Phase 0 - Case intake"
        title="GL ingestion & rule pre-filter"
        description="Ingest a general-ledger extract, normalize each row, and run the deterministic pre-filter. Only flagged rows become investigation cases; clean rows are cleared at intake."
        actions={
          <>
            <Button variant="secondary" onClick={() => setShowPastRuns((open) => !open)}>
              <History className="h-4 w-4" aria-hidden="true" />
              Past runs
            </Button>
            <Button
              disabled={!summary || createCases.isPending || runCases.isPending || deleteImportedCases.isPending}
              onClick={() => {
                if (summary) {
                  void handleCreateCases(summary);
                }
              }}
            >
              <Play className="h-4 w-4" aria-hidden="true" />
              {createCases.isPending ? "Creating cases..." : runCases.isPending ? "Starting crew..." : "Create cases & run crew"}
            </Button>
            <Button
              variant="danger"
              disabled={deleteImportedCases.isPending || createCases.isPending || runCases.isPending}
              onClick={() => void handleDeleteImportedCases()}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {deleteImportedCases.isPending ? "Deleting..." : "Delete imported data"}
            </Button>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
        <Card>
          <CardContent className="space-y-3 p-4">
            <p className="text-sm font-semibold text-foreground">GL data feed</p>
            <input
              ref={inputRef}
              className="sr-only"
              type="file"
              accept=".csv,.tsv,text/csv,text/tab-separated-values"
              aria-label="Upload general ledger CSV or TSV file"
              onChange={(event) => void handleFile(event.target.files?.[0])}
            />
            <button
              type="button"
              className="flex w-full items-center gap-3 rounded-lg border border-dashed border-border bg-background/60 p-4 text-left transition-colors hover:border-primary-border hover:bg-primary-soft/40"
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
              }}
              onDrop={(event) => {
                event.preventDefault();
                void handleFile(event.dataTransfer.files[0]);
              }}
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-success-border bg-success-soft text-success-foreground">
                <FileSpreadsheet className="h-5 w-5" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{summary?.fileName ?? "Upload GL extract"}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  {summary ? `${summary.rowsIngested.toLocaleString()} rows - ${summary.columns.length} columns` : "CSV or TSV"}
                </p>
              </div>
              {uploadedSummary ? <Badge variant="primary">uploaded</Badge> : null}
            </button>
            {uploadError ? <p className="text-xs text-danger-foreground">{uploadError}</p> : null}
            {summary ? <p className="font-mono text-xs text-muted-foreground">{summary.columns.join(" - ")}</p> : null}
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={() => inputRef.current?.click()} disabled={isParsing}>
                <UploadCloud className="h-4 w-4" aria-hidden="true" />
                {isParsing ? "Parsing..." : summary ? "Replace file" : "Upload file"}
              </Button>
              <Button
                size="sm"
                disabled={!summary}
                onClick={() => {
                  if (!summary) {
                    return;
                  }
                  const capped = Math.min(summary.flagged, MAX_CASES_PER_INTAKE_RUN);
                  setRunStatus(
                    `Pre-filter completed for ${summary.fileName}; ${capped} of ${summary.flagged} flagged row(s) ready for case creation.`,
                  );
                }}
              >
                Run pre-filter
              </Button>
              {uploadedSummary ? (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setUploadedSummary(null);
                    setCreateError(null);
                    setRunStatus("Upload a CSV or TSV ledger extract to run the pre-filter.");
                  }}
                >
                  Clear upload
                </Button>
              ) : null}
            </div>
            <p className="rounded-md border border-info-border bg-info-soft px-3 py-2 text-xs text-info-foreground">{runStatus}</p>
            {createError ? <p className="text-xs text-danger-foreground">{createError}</p> : null}
          </CardContent>
        </Card>

        {summary ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {stats.map((stat) => (
              <Card key={stat.label}>
                <CardContent className="p-4">
                  <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">{stat.label}</p>
                  <p className={`mt-2 font-mono text-2xl ${stat.tone}`}>{stat.value}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{stat.helper}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No ledger uploaded"
            description="Upload a CSV or TSV extract to preview deterministic pre-filter results."
            icon={FileSpreadsheet}
          />
        )}
      </div>

      {showPastRuns && intakeRuns.length > 0 ? (
        <Card>
          <CardContent className="space-y-3 p-4">
            <p className="text-sm font-semibold text-foreground">Past intake runs</p>
            {intakeRuns.map((run) => (
              <div
                key={`${run.fileName}-${run.flagged}`}
                className="flex flex-col gap-2 rounded-md border border-border bg-background px-3 py-2 text-sm sm:flex-row sm:items-center"
              >
                <span className="font-medium text-foreground">{run.fileName}</span>
                <span className="text-muted-foreground">{run.rowsIngested.toLocaleString()} rows</span>
                <span className="text-primary">{run.flagged} flagged</span>
                <span className="text-success-foreground">{run.cleared} cleared</span>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {summary ? (
        <div className="grid gap-4 xl:grid-cols-[1fr_1.3fr]">
          <RulePrefilter rules={summary.ruleStats} />
          <FlaggedRowsTable rows={summary.flaggedRows} />
        </div>
      ) : null}

      {summary ? (
        <Card>
          <CardContent className="flex flex-col gap-3 p-4 text-sm text-muted-foreground md:flex-row md:items-center">
            <Info className="h-4 w-4 shrink-0 text-info-foreground" aria-hidden="true" />
            <span className="flex-1">
              {summary.cleared.toLocaleString()} clean rows were recorded as cleared-at-intake and never reach the agent
              crew.
            </span>
            <Button
              className="shrink-0"
              variant="secondary"
              disabled={deleteImportedCases.isPending || createCases.isPending || runCases.isPending || summary.flaggedRows.length === 0}
              onClick={() => void handleCreateCases(summary, { replaceExisting: true })}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {deleteImportedCases.isPending
                ? "Deleting..."
                : createCases.isPending
                  ? "Creating..."
                  : runCases.isPending
                    ? "Starting crew..."
                    : "Replace imported data"}
            </Button>
            <Button
              className="shrink-0"
              disabled={deleteImportedCases.isPending || createCases.isPending || runCases.isPending || summary.flaggedRows.length === 0}
              onClick={() => void handleCreateCases(summary)}
            >
              {createCases.isPending
                ? "Creating..."
                : runCases.isPending
                  ? "Starting crew..."
                  : `Create ${Math.min(summary.flaggedRows.length, MAX_CASES_PER_INTAKE_RUN)} cases`}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
