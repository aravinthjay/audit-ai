import { afterEach, describe, expect, it, vi } from "vitest";

describe("api service behavior", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("throws when the API base URL is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    vi.resetModules();

    const { ApiUnavailableError, apiRequest } = await import("@/services/api");

    await expect(apiRequest("/health")).rejects.toBeInstanceOf(ApiUnavailableError);
  });

  it("returns JSON payloads from successful API responses", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
    vi.resetModules();

    const { apiRequest } = await import("@/services/api");
    const result = await apiRequest<{ total: number }>("/investigations/stats/summary");

    expect(result.total).toBe(1);
  });

  it("surfaces structured API errors", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
    vi.resetModules();

    const { apiRequest } = await import("@/services/api");

    await expect(apiRequest("/missing")).rejects.toMatchObject({ status: 404 });
  });
});
