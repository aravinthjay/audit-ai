import { describe, expect, it } from "vitest";
import { getIntakeSummary, parseLedgerFile } from "@/services/intake.service";

describe("intake service", () => {
  it("starts without a preloaded intake summary", async () => {
    const summary = await getIntakeSummary();

    expect(summary).toBeNull();
  });

  it("parses uploaded CSV files and creates flagged rows", async () => {
    const file = new File(
      [
        [
          "txn_id,date,account,vendor,currency,amount_usd,fx_rate_used,posted_by",
          "TXN-1,2026-06-21T22:10:00Z,Consulting,Unknown Vendor,USD,30000,1.0,admin",
          "TXN-2,2026-06-22T10:00:00Z,Office,Staples,USD,312,1.0,ap.user",
        ].join("\n"),
      ],
      "ledger.csv",
      { type: "text/csv" },
    );

    const summary = await parseLedgerFile(file, { materialityThreshold: 25_000 });

    expect(summary.fileName).toBe("ledger.csv");
    expect(summary.rowsIngested).toBe(2);
    expect(summary.flagged).toBe(1);
    expect(summary.flaggedRows[0].rules).toContain("materiality");
    expect(summary.flaggedRows[0].rules).toContain("unknown vendor");
  });

  it("does not cap flagged rows at 50", async () => {
    const rows = Array.from({ length: 75 }, (_, index) => {
      const id = index + 1;
      return `TXN-${id},2026-06-22T10:00:00Z,Consulting,Vendor ${id},USD,30000,1.0,ap.user`;
    });
    const file = new File(
      [["txn_id,date,account,vendor,currency,amount_usd,fx_rate_used,posted_by", ...rows].join("\n")],
      "large-ledger.csv",
      { type: "text/csv" },
    );

    const summary = await parseLedgerFile(file);

    expect(summary.rowsIngested).toBe(75);
    expect(summary.flagged).toBe(75);
    expect(summary.flaggedRows).toHaveLength(75);
  });
});
