import { describe, expect, it } from "vitest";
import { getDebateArguments } from "@/services/debate.service";

describe("debate service", () => {
  it("maps adjudicator confidence without inventing confidence for debate turns", async () => {
    const rows = await getDebateArguments("case-fixture-1");

    const challenger = rows.find((row) => row.side === "challenger");
    const adjudicator = rows.find((row) => row.side === "adjudicator");

    expect(challenger?.confidence).toBeUndefined();
    expect(adjudicator?.confidence).toBe(0.82);
  });
});
