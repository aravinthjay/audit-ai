import { apiRequest } from "@/services/api";
import { getAgentHealth } from "@/services/agents.service";
import type {
  AgentHealth,
  DashboardSummary,
  Investigation,
  InvestigationStatus,
  Metric,
  ReviewQueueItem,
  RiskDistributionItem,
  RiskLevel,
} from "@/types/domain";

type ApiInvestigation = {
  id: string;
  transaction_id: string;
  vendor: string;
  category: string;
  amount: number;
  risk?: string | null;
  confidence?: number | null;
  flags?: string[] | null;
  status: string;
  owner?: string | null;
  reviewer?: string | null;
  posted_at?: string | null;
  due_at?: string | null;
  materiality?: number | null;
  description?: string | null;
  created_at: string;
};

type ApiInvestigationList = {
  total: number;
  investigations: ApiInvestigation[];
};

type ApiStatsSummary = {
  total: number;
  avg_confidence: number;
  by_risk: Partial<Record<RiskLevel, number>>;
  by_status: Partial<Record<InvestigationStatus, number>>;
  auto_cleared: number;
  in_review: number;
  manual: number;
};

type ApiReviewQueueItem = {
  id: string;
  investigation_id: string;
  title: string;
  risk?: string | null;
  confidence?: number | null;
  due_at?: string | null;
  queue?: "reviewer" | "partner";
  assigned_to?: string | null;
  priority?: number | null;
  status?: string | null;
  notes?: string | null;
};

export type CreateInvestigationInput = {
  transactionId: string;
  vendor: string;
  category: string;
  amount: number;
  materiality?: number;
  description?: string;
  owner?: string;
};

const riskLevels: RiskLevel[] = ["critical", "high", "medium", "low", "cleared"];
const investigationStatuses: InvestigationStatus[] = [
  "intake",
  "collecting_evidence",
  "agent_debate",
  "verification",
  "human_review",
  "report_ready",
  "closed",
  "failed",
];

function isRiskLevel(value: string | null | undefined): value is RiskLevel {
  return riskLevels.includes(value as RiskLevel);
}

function isInvestigationStatus(value: string | null | undefined): value is InvestigationStatus {
  return investigationStatuses.includes(value as InvestigationStatus);
}

function formatDate(value?: string | null) {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 10);
  }

  return date.toISOString().slice(0, 10);
}

function dueDateFrom(createdAt: string) {
  const date = new Date(createdAt);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  date.setDate(date.getDate() + 7);
  return date.toISOString().slice(0, 10);
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function mapInvestigation(row: ApiInvestigation): Investigation {
  const risk = isRiskLevel(row.risk) ? row.risk : "medium";
  const status = isInvestigationStatus(row.status) ? row.status : "failed";
  const postedAt = formatDate(row.posted_at ?? row.created_at);

  return {
    id: row.id,
    transactionId: row.transaction_id,
    vendor: row.vendor,
    category: row.category,
    amount: row.amount,
    confidence: row.confidence ?? 0,
    risk,
    flags: row.flags?.length ? row.flags : [`${risk} risk`, status.replaceAll("_", " ")],
    status,
    owner: row.owner ?? "Unassigned",
    reviewer: row.reviewer ?? undefined,
    postedAt,
    dueAt: formatDate(row.due_at) || dueDateFrom(row.created_at),
    materiality: row.materiality ?? 0,
    description: row.description ?? "No case description has been recorded yet.",
  };
}

function riskDistributionFromStats(stats: ApiStatsSummary): RiskDistributionItem[] {
  const totalRisk = riskLevels.reduce((sum, risk) => sum + (stats.by_risk[risk] ?? 0), 0);
  const denominator = Math.max(totalRisk, 1);

  return riskLevels.map((risk) => {
    const count = stats.by_risk[risk] ?? 0;

    return {
      label: risk,
      count,
      percent: count / denominator,
    };
  });
}

function metricsFromStats(stats: ApiStatsSummary): Metric[] {
  const critical = stats.by_risk.critical ?? 0;
  const high = stats.by_risk.high ?? 0;
  const medium = stats.by_risk.medium ?? 0;
  const low = stats.by_risk.low ?? 0;
  const closed = stats.by_status.closed ?? 0;
  const open = Math.max(stats.total - closed, 0);

  return [
    {
      label: "Total cases",
      value: formatNumber(stats.total),
      helper: `${formatNumber(open)} open investigations`,
    },
    {
      label: "Open investigations",
      value: formatNumber(open),
      helper: `${formatNumber(closed)} closed`,
    },
    {
      label: "Critical or high-risk",
      value: formatNumber(critical + high),
      helper: `${formatNumber(critical)} critical`,
      tone: critical > 0 || high > 0 ? "danger" : "success",
    },
    {
      label: "Medium-risk cases",
      value: formatNumber(medium),
      helper: "pending analysis",
      tone: medium > 0 ? "warning" : "success",
    },
    {
      label: "Low-risk cases",
      value: formatNumber(low),
      helper: "ready for auto-clear",
      tone: "success",
    },
    {
      label: "Pending human review",
      value: formatNumber(stats.in_review),
      helper: "awaiting reviewer action",
      tone: stats.in_review > 0 ? "warning" : "success",
    },
    {
      label: "Partner escalation",
      value: formatNumber(critical),
      helper: "critical risk queue",
      tone: critical > 0 ? "danger" : "success",
    },
    {
      label: "Average confidence",
      value: stats.avg_confidence.toFixed(2),
      helper: "across active cases",
      tone: stats.avg_confidence >= 0.8 ? "success" : "warning",
    },
  ];
}

function mapDashboard(
  stats: ApiStatsSummary,
  investigations: Investigation[],
  agentHealth: AgentHealth[],
): DashboardSummary {
  return {
    engagement: "Skeptic Engine",
    period: "Live backend",
    metrics: metricsFromStats(stats),
    riskDistribution: riskDistributionFromStats(stats),
    throughput: {
      autoCleared: stats.auto_cleared,
      inReview: stats.in_review,
      manual: stats.manual,
    },
    agentHealth,
    recentInvestigations: investigations.slice(0, 4),
  };
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const [stats, list, agentHealth] = await Promise.all([
    apiRequest<ApiStatsSummary>("/investigations/stats/summary"),
    apiRequest<ApiInvestigationList>("/investigations?limit=10"),
    getAgentHealth(),
  ]);

  return mapDashboard(stats, list.investigations.map(mapInvestigation), agentHealth);
}

export async function getInvestigations(options: { hasDebate?: boolean } = {}): Promise<Investigation[]> {
  const query = options.hasDebate ? "/investigations?limit=500&has_debate=true" : "/investigations?limit=500";
  const payload = await apiRequest<ApiInvestigationList>(query);
  return payload.investigations.map(mapInvestigation);
}

export async function getInvestigation(caseId: string): Promise<Investigation | undefined> {
  if (!caseId) {
    return undefined;
  }

  return mapInvestigation(await apiRequest<ApiInvestigation>(`/investigations/${caseId}`));
}

export async function getReviewQueue(): Promise<ReviewQueueItem[]> {
  const queue = await apiRequest<ApiReviewQueueItem[]>("/reviews/queue");

  return queue.map((item) => ({
    id: item.id,
    caseId: item.investigation_id,
    title: item.title,
    risk: isRiskLevel(item.risk) ? item.risk : "medium",
    confidence: item.confidence ?? 0,
    dueAt: formatDate(item.due_at) || "unscheduled",
    queue: item.queue ?? "reviewer",
    assignedTo: item.assigned_to ?? undefined,
    priority: item.priority ?? 3,
    status: item.status ?? "pending",
    notes: item.notes ?? undefined,
  }));
}

export async function createInvestigation(input: CreateInvestigationInput): Promise<Investigation> {
  const payload = {
    transaction_id: input.transactionId,
    vendor: input.vendor,
    category: input.category,
    amount: input.amount,
    materiality: input.materiality,
    description: input.description,
    owner: input.owner,
  };

  return mapInvestigation(
    await apiRequest<ApiInvestigation>("/investigations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  );
}

export async function createInvestigations(inputs: CreateInvestigationInput[]): Promise<Investigation[]> {
  const created: Investigation[] = [];

  for (const input of inputs) {
    created.push(await createInvestigation(input));
  }

  return created;
}

export type ExecuteInvestigationResponse = {
  investigation_id: string;
  task_id?: string | null;
  status: string;
  message: string;
};

export type DeleteImportedInvestigationsResponse = {
  deleted_count: number;
  investigation_ids: string[];
  message: string;
};

export async function deleteImportedInvestigations(): Promise<DeleteImportedInvestigationsResponse> {
  return apiRequest<DeleteImportedInvestigationsResponse>("/investigations/imported", {
    method: "DELETE",
  });
}

export async function executeInvestigation(caseId: string): Promise<ExecuteInvestigationResponse> {
  return apiRequest<{ investigation_id: string; task_id?: string | null; status: string; message: string }>(
    `/investigations/${caseId}/execute`,
    { method: "POST" },
  );
}

export async function executeInvestigations(caseIds: string[]): Promise<ExecuteInvestigationResponse[]> {
  const results: ExecuteInvestigationResponse[] = [];

  for (const caseId of caseIds) {
    results.push(await executeInvestigation(caseId));
  }

  return results;
}
