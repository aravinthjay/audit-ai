import { describe, expect, it } from "vitest";
import { riskLabel, riskTone, stateTone, statusLabel } from "@/lib/status";

describe("status helpers", () => {
  it("maps risk levels to labels and tones", () => {
    expect(riskLabel("critical")).toBe("Critical");
    expect(riskTone("critical")).toBe("danger");
    expect(riskTone("cleared")).toBe("success");
  });

  it("maps workflow states to display tones", () => {
    expect(stateTone("running")).toBe("primary");
    expect(stateTone("blocked")).toBe("danger");
  });

  it("formats snake case status labels", () => {
    expect(statusLabel("human_review")).toBe("Human Review");
  });
});
