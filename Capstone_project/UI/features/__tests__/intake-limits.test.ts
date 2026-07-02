import { describe, expect, it } from "vitest";
import {
  heldBackCaseCount,
  MAX_CASES_PER_INTAKE_RUN,
  rowsForCaseCreation,
} from "@/features/intake/intake-limits";

describe("intake case creation limits", () => {
  it("creates at most 50 cases per intake run", () => {
    const rows = Array.from({ length: 75 }, (_, index) => ({ id: index + 1 }));

    const limited = rowsForCaseCreation(rows);

    expect(MAX_CASES_PER_INTAKE_RUN).toBe(50);
    expect(limited).toHaveLength(50);
    expect(limited.at(-1)?.id).toBe(50);
    expect(heldBackCaseCount(rows.length)).toBe(25);
  });
});
