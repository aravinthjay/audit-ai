import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { AuditLogsView } from "@/features/audit/audit-logs-view";
import { DashboardView } from "@/features/dashboard/dashboard-view";
import { DebateView } from "@/features/debate/debate-view";
import { EvaluationView } from "@/features/evaluation/evaluation-view";
import { EvidenceView } from "@/features/evidence/evidence-view";
import { IntakeView } from "@/features/intake/intake-view";
import { ReportsView } from "@/features/reports/reports-view";
import { ReplayView } from "@/features/replay/replay-view";
import { SettingsView } from "@/features/settings/settings-view";
import { VerificationView } from "@/features/verification/verification-view";

function createWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe("feature views render with data", () => {
  it("renders the Case Intake page", async () => {
    render(<IntakeView />, { wrapper: createWrapper() });

    expect(await screen.findByText("No ledger uploaded")).toBeInTheDocument();
    expect(await screen.findByText("Upload file")).toBeInTheDocument();
  });

  it("renders the RAGAS Evaluation page", async () => {
    render(<EvaluationView />, { wrapper: createWrapper() });

    expect(await screen.findByText(/RAGAS evaluation/i)).toBeInTheDocument();
    expect(await screen.findByText("No evaluation results")).toBeInTheDocument();
  });

  it("renders the Audit Log page", async () => {
    render(<AuditLogsView />, { wrapper: createWrapper() });

    expect(await screen.findByText("Replay timeline")).toBeInTheDocument();
  });

  it("renders case-scoped investigation pages from the active case", async () => {
    const debate = render(<DebateView />, { wrapper: createWrapper() });
    expect(await screen.findByText("Challenger and defender exchange")).toBeInTheDocument();
    debate.unmount();

    const evidence = render(<EvidenceView />, { wrapper: createWrapper() });
    expect(await screen.findByText("Source-grounded evidence")).toBeInTheDocument();
    evidence.unmount();

    const verification = render(<VerificationView />, { wrapper: createWrapper() });
    expect(await screen.findByText("Claim grounding")).toBeInTheDocument();
    verification.unmount();

    const replay = render(<ReplayView />, { wrapper: createWrapper() });
    expect(await screen.findByText("No replay frames")).toBeInTheDocument();
    replay.unmount();

    render(<ReportsView />, { wrapper: createWrapper() });
    expect(await screen.findByText("Professional skepticism reports")).toBeInTheDocument();
  });

  it("renders the Dashboard page", async () => {
    render(<DashboardView />, { wrapper: createWrapper() });

    expect((await screen.findAllByText(/Skeptic Engine/i)).length).toBeGreaterThan(0);
  });

  it("renders the Settings page with LLM provider routing", async () => {
    render(<SettingsView />, { wrapper: createWrapper() });

    expect(await screen.findByText("LLM provider routing")).toBeInTheDocument();
    expect(await screen.findByText("Model and threshold policy")).toBeInTheDocument();
  });
});
