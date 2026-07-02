import { describe, expect, it } from "vitest";
import {
  getEvidenceVerification,
  verifyEvidence,
} from "@/services/evidence-verification.service";

describe("evidence verification service", () => {
  it("loads the latest third-party evidence verification", async () => {
    const result = await getEvidenceVerification("case-fixture-1");

    expect(result?.verificationStatus).toBe("API_UNAVAILABLE");
    expect(result?.providerName).toBe("generic_third_party_provider");
    expect(result?.tolerancePercentage).toBe(0.3);
  });

  it("can re-run verification for a claim", async () => {
    const result = await verifyEvidence("case-fixture-1");

    expect(result.verificationStatus).toBe("FLAGGED");
    expect(result.fetchedAmount).toBe(7500);
    expect(result.differencePercentage).toBeGreaterThan(1);
  });
});
