import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    refresh: vi.fn(),
  }),
}));

process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1";
process.env.NEXT_PUBLIC_API_USERNAME = "";
process.env.NEXT_PUBLIC_API_PASSWORD = "";
process.env.NEXT_PUBLIC_API_TOKEN = "";

const investigation = {
  id: "case-fixture-1",
  transaction_id: "TXN-001",
  vendor: "Live Vendor Ltd",
  category: "consulting",
  amount: 75000,
  risk: "high",
  confidence: 0.82,
  flags: ["high risk", "human review"],
  status: "human_review",
  owner: "Audit team",
  reviewer: "Reviewer",
  posted_at: "2026-06-21T10:00:00Z",
  due_at: "2026-06-28T10:00:00Z",
  materiality: 50000,
  description: "Fixture investigation loaded through the API service layer.",
  created_at: "2026-06-21T10:00:00Z",
};

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

globalThis.fetch = async (input, init) => {
  const method = input instanceof Request ? input.method : init?.method ?? "GET";
  const rawUrl = input instanceof Request ? input.url : String(input);
  const url = new URL(rawUrl);
  const path = url.pathname.replace(/^\/api\/v1/, "");

  if (path === "/investigations/stats/summary") {
    return jsonResponse({
      total: 1,
      avg_confidence: 0.82,
      by_risk: { high: 1 },
      by_status: { human_review: 1 },
      auto_cleared: 0,
      in_review: 1,
      manual: 1,
    });
  }

  if (path === "/agents/health") {
    return jsonResponse([
      {
        label: "Supervisor",
        state: "review",
        latency: "1 in review",
        load: 1,
      },
    ]);
  }

  if (path === `/agents/workflow/${investigation.id}`) {
    return jsonResponse([
      {
        id: "intake",
        role: "Supervisor",
        state: "done",
        detail: "Case TXN-001 is registered for Live Vendor Ltd.",
        latency: "updated 2026-06-21T10:00:00",
        confidence: null,
        token_usage: 0,
        cost: 0,
        attempt: 1,
        expanded_detail: "Fixture investigation loaded through the API service layer.",
      },
    ]);
  }

  if (path === "/settings") {
    return jsonResponse({
      reasoning_model: "claude-3-5-sonnet-20241022",
      report_model: "claude-3-5-haiku-20241022",
      auto_clear_threshold: 0.7,
      reviewer_threshold: 0.5,
      materiality: 50000,
      segregation_of_duties: true,
      immutable_audit_log: true,
      debate_round_cap: 2,
      api_key_vault: "environment",
      theme: "system",
      display_currency: "USD",
      notifications: false,
      audit_retention_years: 7,
      ip_allowlist: false,
      estimated_agent_run_cost_usd: 0.21,
    });
  }

  if (path === "/settings/llm") {
    if (method === "PUT") {
      const body =
        input instanceof Request
          ? ((await input.json()) as Record<string, unknown>)
          : init?.body
            ? (JSON.parse(String(init.body)) as Record<string, unknown>)
            : {};

      return jsonResponse({
        default_provider: body.default_provider ?? "groq",
        active_provider: body.default_provider ?? "groq",
        fallback_enabled: body.fallback_enabled ?? true,
        fallback_order: body.fallback_order ?? ["anthropic", "openai"],
        providers: [
          {
            id: "anthropic",
            label: "Claude / Anthropic",
            configured: true,
            reasoning_model: "claude-3-5-sonnet-20241022",
            lightweight_model: "claude-3-5-haiku-20241022",
            missing_env: null,
          },
          {
            id: "groq",
            label: "Groq",
            configured: true,
            reasoning_model: "llama-3.3-70b-versatile",
            lightweight_model: "llama-3.1-8b-instant",
            missing_env: null,
          },
          {
            id: "openai",
            label: "OpenAI",
            configured: false,
            reasoning_model: "gpt-4.1",
            lightweight_model: "gpt-4.1-mini",
            missing_env: "OPENAI_API_KEY",
          },
        ],
      });
    }

    return jsonResponse({
      default_provider: "anthropic",
      active_provider: "anthropic",
      fallback_enabled: true,
      fallback_order: ["groq", "openai"],
      providers: [
        {
          id: "anthropic",
          label: "Claude / Anthropic",
          configured: true,
          reasoning_model: "claude-3-5-sonnet-20241022",
          lightweight_model: "claude-3-5-haiku-20241022",
          missing_env: null,
        },
        {
          id: "groq",
          label: "Groq",
          configured: true,
          reasoning_model: "llama-3.3-70b-versatile",
          lightweight_model: "llama-3.1-8b-instant",
          missing_env: null,
        },
        {
          id: "openai",
          label: "OpenAI",
          configured: false,
          reasoning_model: "gpt-4.1",
          lightweight_model: "gpt-4.1-mini",
          missing_env: "OPENAI_API_KEY",
        },
      ],
    });
  }

  if (path === "/settings/llm/providers") {
    return jsonResponse([
      {
        id: "anthropic",
        label: "Claude / Anthropic",
        configured: true,
        reasoning_model: "claude-3-5-sonnet-20241022",
        lightweight_model: "claude-3-5-haiku-20241022",
        missing_env: null,
      },
      {
        id: "groq",
        label: "Groq",
        configured: true,
        reasoning_model: "llama-3.3-70b-versatile",
        lightweight_model: "llama-3.1-8b-instant",
        missing_env: null,
      },
      {
        id: "openai",
        label: "OpenAI",
        configured: false,
        reasoning_model: "gpt-4.1",
        lightweight_model: "gpt-4.1-mini",
        missing_env: "OPENAI_API_KEY",
      },
    ]);
  }

  if (path === "/intake/summary") {
    return jsonResponse(null);
  }

  if (path === "/investigations" && method === "POST") {
    const body =
      input instanceof Request
        ? ((await input.json()) as Record<string, unknown>)
        : init?.body
          ? (JSON.parse(String(init.body)) as Record<string, unknown>)
          : {};

    return jsonResponse(
      {
        ...investigation,
        id: "case-created-1",
        transaction_id: body.transaction_id ?? "TXN-CREATED",
        vendor: body.vendor ?? "Created Vendor",
        category: body.category ?? "created",
        amount: body.amount ?? 1000,
        materiality: body.materiality ?? 25000,
        description: body.description ?? "Created from test.",
        owner: body.owner ?? "intake",
      },
      201,
    );
  }

  if (path === "/investigations/imported" && method === "DELETE") {
    return jsonResponse({
      deleted_count: 2,
      investigation_ids: ["case-imported-1", "case-imported-2"],
      message: "Deleted 2 imported intake investigation(s).",
    });
  }

  if (path === "/investigations") {
    return jsonResponse({ total: 1, skip: 0, limit: 500, investigations: [investigation] });
  }

  if (path === `/investigations/${investigation.id}`) {
    return jsonResponse(investigation);
  }

  if (path.match(/^\/investigations\/[^/]+\/execute$/) && method === "POST") {
    const caseId = path.split("/")[2];

    return jsonResponse({
      investigation_id: caseId,
      task_id: null,
      status: "running",
      message: "Investigation running in-process",
    });
  }

  if (path === `/investigations/${investigation.id}/debate`) {
    return jsonResponse([
      {
        id: "debate-1",
        round: 1,
        speaker: "Challenger",
        message: "Question the related-party rationale.",
        token_count: 120,
        created_at: "2026-06-21T11:00:00Z",
      },
      {
        id: "debate-2",
        round: 2,
        speaker: "adjudicator",
        message: "Verdict: high risk at 82% confidence.",
        token_count: 90,
        confidence: 0.82,
        created_at: "2026-06-21T11:05:00Z",
      },
    ]);
  }

  if (path === `/investigations/${investigation.id}/evidence`) {
    return jsonResponse([
      {
        id: "evidence-1",
        source: "Ledger",
        content: "Payment exceeds materiality.",
        citations: ["ledger/TXN-001"],
        relevance_score: 0.9,
        created_at: "2026-06-21T11:00:00Z",
      },
    ]);
  }

  if (path === `/investigations/${investigation.id}/verification`) {
    return jsonResponse([
      {
        id: "verification-1",
        claim_text: "Payment exceeds materiality.",
        is_grounded: true,
        explanation: "Ledger evidence supports the claim.",
        supporting_evidence: ["evidence-1"],
        created_at: "2026-06-21T11:10:00Z",
      },
    ]);
  }

  if (path === `/claims/${investigation.id}/verification`) {
    return jsonResponse({
      id: "evidence-verification-1",
      claim_id: investigation.id,
      category: "generic",
      claimed_amount: 75000,
      fetched_amount: null,
      min_acceptable_amount: null,
      max_acceptable_amount: null,
      difference_amount: null,
      difference_percentage: null,
      tolerance_percentage: 0.3,
      provider_name: "generic_third_party_provider",
      provider_reference_id: null,
      verification_status: "API_UNAVAILABLE",
      confidence_score: 0,
      reason: "No real-time third-party provider URL is configured for category 'generic'.",
      created_at: "2026-06-21T10:01:00Z",
      updated_at: "2026-06-21T10:01:00Z",
    });
  }

  if (path.match(/^\/claims\/[^/]+\/verify-evidence$/) && method === "POST") {
    const caseId = path.split("/")[2];

    return jsonResponse(
      {
        id: "evidence-verification-rerun-1",
        claim_id: caseId,
        category: "flight",
        claimed_amount: 20000,
        fetched_amount: 7500,
        min_acceptable_amount: 5625,
        max_acceptable_amount: 9375,
        difference_amount: 12500,
        difference_percentage: 1.666667,
        tolerance_percentage: 0.25,
        provider_name: "live_flight_fare_api",
        provider_reference_id: "LIVE-FLIGHT-123",
        verification_status: "FLAGGED",
        confidence_score: 0.78,
        reason: "Claimed amount is outside the accepted +/-25% range.",
        created_at: "2026-06-21T10:02:00Z",
        updated_at: "2026-06-21T10:02:00Z",
      },
      201,
    );
  }

  if (path === `/investigations/${investigation.id}/audit`) {
    return jsonResponse([
      {
        id: "audit-1",
        type: "case_created",
        data: {
          event_type: "case_created",
          investigation_id: investigation.id,
          actor: "system",
          details: {},
          timestamp: "2026-06-21T10:00:00Z",
        },
        hash: "abcdef1234567890",
        sequence: 1,
      },
    ]);
  }

  if (path === `/investigations/${investigation.id}/replay`) {
    return jsonResponse([]);
  }

  if (path === "/evaluation/summary") {
    return jsonResponse({ cases: 0, metrics: [], conclusion: "" });
  }

  if (path === "/analytics/trend" || path === "/analytics/agent-accuracy" || path === "/analytics/kpis") {
    return jsonResponse([]);
  }

  if (path === "/analytics/requests") {
    return jsonResponse({
      total_requests: 4,
      error_rate: 0,
      avg_duration_ms: 42.5,
      p95_duration_ms: 88.1,
      by_status: { "200": 4 },
      top_paths: [{ path: "/api/v1/investigations", count: 2 }],
      recent: [
        {
          request_id: "req-test-1",
          method: "GET",
          path: "/api/v1/investigations",
          status_code: 200,
          duration_ms: 42.5,
          created_at: "2026-07-01T10:00:00",
        },
      ],
    });
  }

  if (path.startsWith("/analytics/llm/summary")) {
    return jsonResponse({
      total_tokens: 12500,
      prompt_tokens: 9000,
      completion_tokens: 3500,
      total_estimated_cost_usd: 0.0425,
      total_actual_cost_usd: null,
      successful_calls: 7,
      failed_calls: 1,
      fallback_calls: 2,
      cache_hits: 1,
      average_latency_ms: 820,
      most_expensive_request_types: [{ request_type: "adjudication", estimated_cost_usd: 0.03 }],
    });
  }

  if (path.startsWith("/analytics/llm/by-provider")) {
    return jsonResponse([
      {
        provider_name: "anthropic",
        calls: 4,
        total_tokens: 9000,
        prompt_tokens: 6500,
        completion_tokens: 2500,
        total_estimated_cost_usd: 0.035,
        total_actual_cost_usd: null,
        successful_calls: 4,
        failed_calls: 0,
        fallback_calls: 0,
        cache_hits: 1,
        average_latency_ms: 900,
        most_expensive_request_types: [],
      },
      {
        provider_name: "groq",
        calls: 3,
        total_tokens: 3500,
        prompt_tokens: 2500,
        completion_tokens: 1000,
        total_estimated_cost_usd: 0.0075,
        total_actual_cost_usd: null,
        successful_calls: 3,
        failed_calls: 1,
        fallback_calls: 2,
        cache_hits: 0,
        average_latency_ms: 420,
        most_expensive_request_types: [],
      },
    ]);
  }

  if (path.startsWith("/analytics/llm/by-model")) {
    return jsonResponse([
      {
        model_name: "claude-3-5-sonnet-20241022",
        calls: 4,
        total_tokens: 9000,
        prompt_tokens: 6500,
        completion_tokens: 2500,
        total_estimated_cost_usd: 0.035,
        total_actual_cost_usd: null,
        successful_calls: 4,
        failed_calls: 0,
        fallback_calls: 0,
        cache_hits: 1,
        average_latency_ms: 900,
        most_expensive_request_types: [],
      },
    ]);
  }

  if (path.startsWith("/analytics/llm/recent-calls")) {
    return jsonResponse([
      {
        id: "llm-call-1",
        provider_name: "anthropic",
        model_name: "claude-3-5-sonnet-20241022",
        request_type: "adjudication",
        prompt_tokens: 1200,
        completion_tokens: 420,
        total_tokens: 1620,
        estimated_cost_usd: 0.01,
        actual_cost_usd: null,
        latency_ms: 860,
        success: true,
        error_message: null,
        fallback_used: false,
        fallback_provider: null,
        cache_hit: false,
        model_tier: "reasoning",
        routing_reason: "complex or audit-critical request uses the stronger reasoning model",
        quality_guardrail: "Preserve citations.",
        user_id: null,
        session_id: null,
        request_id: "req-llm-1",
        created_at: "2026-07-01T10:00:00",
      },
    ]);
  }

  if (path.startsWith("/analytics/llm/cost-trends")) {
    return jsonResponse([
      {
        period: "2026-07-01",
        calls: 7,
        total_tokens: 12500,
        estimated_cost_usd: 0.0425,
        fallback_calls: 2,
        average_latency_ms: 820,
      },
    ]);
  }

  if (path === "/reports") {
    return jsonResponse([]);
  }

  if (path === "/knowledge/sources") {
    return jsonResponse([
      {
        id: "kb-approval-matrix",
        title: "Delegated Approval Matrix",
        description: "Spend authority limits by role.",
        owner: "Controllership",
        count: "1 chunks",
        freshness: "Updated today",
        status: "synced",
        clause_preview: "Payments above 25000 require dual approval.",
        version_history: ["v4.2 (current)"],
        citation_ids: ["approval-matrix-4.2-sec-2.1"],
        embedding_status: "indexed",
      },
    ]);
  }

  if (path === "/knowledge/chunks") {
    return jsonResponse([
      {
        id: "approval-matrix-4.2-sec-2.1",
        source_id: "kb-approval-matrix",
        source_title: "Delegated Approval Matrix",
        section: "2.1",
        title: "Dual Approval Threshold",
        content: "Payments above 25000 require dual approval.",
        keywords: ["approval", "threshold"],
      },
    ]);
  }

  if (path.startsWith("/knowledge/search")) {
    return jsonResponse([
      {
        id: "approval-matrix-4.2-sec-2.1",
        source_id: "kb-approval-matrix",
        source_title: "Delegated Approval Matrix",
        section: "2.1",
        title: "Dual Approval Threshold",
        content: "Payments above 25000 require dual approval.",
        keywords: ["approval", "threshold"],
        score: 4.2,
        lexical_score: 3,
        vector_score: 0.4,
      },
    ]);
  }

  if (path === "/knowledge/reindex") {
    return jsonResponse({ status: "success", synced_chunks: 1 });
  }

  if (path === "/audit/recent") {
    return jsonResponse([]);
  }

  if (path === "/reviews/queue") {
    return jsonResponse([
      {
        id: "queue-1",
        investigation_id: investigation.id,
        title: "Live Vendor Ltd / consulting",
        risk: "high",
        confidence: 0.82,
        due_at: "2026-06-28T10:00:00Z",
        queue: "reviewer",
        assigned_to: "reviewer_pool",
        priority: 2,
        status: "pending",
        notes: "Confidence gate routed case to review.",
      },
    ]);
  }

  return jsonResponse({ detail: "Unhandled test endpoint" }, 404);
};
