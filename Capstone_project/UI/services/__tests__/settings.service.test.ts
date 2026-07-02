import { describe, expect, it } from "vitest";
import { getLlmSettings, updateLlmSettings } from "@/services/settings.service";

describe("settings service", () => {
  it("maps LLM provider settings", async () => {
    const settings = await getLlmSettings();

    expect(settings.defaultProvider).toBe("anthropic");
    expect(settings.fallbackEnabled).toBe(true);
    expect(settings.providers).toContainEqual(
      expect.objectContaining({ id: "groq", label: "Groq", configured: true }),
    );
  });

  it("updates LLM provider settings through the backend", async () => {
    const settings = await updateLlmSettings({
      defaultProvider: "groq",
      fallbackEnabled: true,
      fallbackOrder: ["anthropic", "openai"],
    });

    expect(settings.defaultProvider).toBe("groq");
    expect(settings.fallbackOrder).toEqual(["anthropic", "openai"]);
  });
});
