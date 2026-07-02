/**
 * Turn raw backend / LLM-provider error strings into clear, human messages with a
 * hint on how to fix them. Keeps the underlying text available for debugging.
 */
export type FriendlyError = {
  title: string;
  detail: string;
  raw: string;
  isError: boolean;
};

export function friendlyError(raw: string | null | undefined): FriendlyError {
  const text = (raw ?? "").toString();
  const t = text.toLowerCase();
  const isError = t.includes("failed") || t.includes("error") || t.includes("unable") || t.includes("could not");

  const make = (title: string, detail: string): FriendlyError => ({ title, detail, raw: text, isError: true });

  if (
    t.includes("invalid_api_key") ||
    t.includes("incorrect api key") ||
    t.includes("invalid x-api-key") ||
    t.includes("unauthorized") ||
    t.includes("placeholder") ||
    (t.includes("api key") && (t.includes("invalid") || t.includes("incorrect") || t.includes("missing")))
  ) {
    return make(
      "Model API key problem",
      "A model provider's API key is missing, invalid, or still a placeholder. Add a valid key for your selected provider (Settings → LLM provider routing, or the backend .env).",
    );
  }
  if (t.includes("quota") || t.includes("rate limit") || t.includes("rate_limit") || t.includes("429") || t.includes("too many requests")) {
    return make(
      "Provider rate-limited or out of quota",
      "The model provider hit its rate limit or free-tier quota. It automatically tries the next provider — wait a moment, run smaller batches, or add billing.",
    );
  }
  if (t.includes("not_found") || t.includes("not found") || t.includes("does not exist") || /model:\s/.test(t)) {
    return make(
      "Model not available",
      "The configured model name isn't available for your key (providers retire model IDs). Update the model in the backend .env, then retry.",
    );
  }
  if (t.includes("timeout") || t.includes("timed out")) {
    return make(
      "Request timed out",
      "The model took too long to respond. It will retry automatically; try again if it keeps happening.",
    );
  }
  if (t.includes("no llm provider") || t.includes("not configured") || t.includes("no usable")) {
    return make(
      "No usable model provider",
      "None of the configured providers has a valid API key. Add at least one working key (Groq and Gemini are free) in Settings / .env.",
    );
  }
  if (t.includes("network") || t.includes("connection") || t.includes("econnrefused") || t.includes("fetch")) {
    return make(
      "Can't reach the backend",
      "The UI couldn't reach the API. Check that the backend is running and NEXT_PUBLIC_API_BASE_URL is correct.",
    );
  }

  return { title: isError ? "Something went wrong" : "", detail: text, raw: text, isError };
}
