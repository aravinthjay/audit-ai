import { describe, expect, it } from "vitest";
import {
  createInvestigations,
  deleteImportedInvestigations,
  executeInvestigations,
  getDashboardSummary,
  getInvestigation,
  getInvestigations,
  getReviewQueue,
} from "@/services/cases.service";

describe("cases service", () => {
  it("returns dashboard summary with recent investigations", async () => {
    const summary = await getDashboardSummary();

    expect(summary.engagement).toBe("Skeptic Engine");
    expect(summary.recentInvestigations.length).toBeGreaterThan(0);
    expect(summary.metrics.some((metric) => metric.label === "Average confidence")).toBe(true);
  });

  it("looks up a case by id", async () => {
    const investigation = await getInvestigation("case-fixture-1");

    expect(investigation?.vendor).toBe("Live Vendor Ltd");
    expect(investigation?.risk).toBe("high");
  });

  it("keeps review queue scoped to cases needing human judgement", async () => {
    const investigations = await getInvestigations();
    const queue = await getReviewQueue();
    const queueCaseIds = new Set(queue.map((item) => item.caseId));

    expect(queue.length).toBeGreaterThan(0);
    expect(investigations.some((item) => queueCaseIds.has(item.id))).toBe(true);
    expect(queue.every((item) => item.confidence < 1)).toBe(true);
  });

  it("creates investigations through the backend API", async () => {
    const created = await createInvestigations([
      {
        transactionId: "TXN-CREATED",
        vendor: "Created Vendor",
        category: "consulting",
        amount: 12500,
        materiality: 25000,
        description: "Created from test.",
        owner: "intake",
      },
    ]);

    expect(created).toHaveLength(1);
    expect(created[0].transactionId).toBe("TXN-CREATED");
    expect(created[0].vendor).toBe("Created Vendor");
  });

  it("starts execution for created investigations", async () => {
    const results = await executeInvestigations(["case-created-1", "case-created-2"]);

    expect(results).toHaveLength(2);
    expect(results[0]).toMatchObject({
      investigation_id: "case-created-1",
      status: "running",
    });
  });

  it("deletes imported intake investigations through the backend API", async () => {
    const result = await deleteImportedInvestigations();

    expect(result.deleted_count).toBe(2);
    expect(result.investigation_ids).toContain("case-imported-1");
  });
});
