type ApiRequestOptions = RequestInit & {
  auth?: boolean;
};

export class ApiUnavailableError extends Error {
  constructor() {
    super("API base URL is not configured.");
    this.name = "ApiUnavailableError";
  }
}

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ?? "";
let tokenPromise: Promise<string | null> | null = null;

export function isApiConfigured() {
  return apiBaseUrl.length > 0;
}

export function apiWebSocketUrl(path: string) {
  if (!isApiConfigured()) {
    return "";
  }

  const url = new URL(apiBaseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
  url.search = "";
  return url.toString();
}

function getStaticToken() {
  return process.env.NEXT_PUBLIC_API_TOKEN?.trim() || null;
}

async function requestPasswordToken() {
  const username = process.env.NEXT_PUBLIC_API_USERNAME?.trim();
  const password = process.env.NEXT_PUBLIC_API_PASSWORD?.trim();

  if (!username || !password) {
    return null;
  }

  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const response = await fetch(`${apiBaseUrl}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as { access_token?: string };
  return payload.access_token ?? null;
}

async function getAccessToken() {
  const staticToken = getStaticToken();

  if (staticToken) {
    return staticToken;
  }

  tokenPromise ??= requestPasswordToken();
  return tokenPromise;
}

async function parseResponse(response: Response) {
  const contentType = response.headers.get("content-type") ?? "";

  if (response.status === 204) {
    return undefined;
  }

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  if (!isApiConfigured()) {
    throw new ApiUnavailableError();
  }

  const { auth = true, ...requestInit } = options;
  const headers = new Headers(requestInit.headers);
  const hasBody = requestInit.body !== undefined;

  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (auth) {
    const token = await getAccessToken();

    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...requestInit,
    headers,
    cache: requestInit.cache ?? "no-store",
  });
  const payload = await parseResponse(response);

  if (!response.ok) {
    const message =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `API request failed with status ${response.status}`;

    throw new ApiError(response.status, message, payload);
  }

  return payload as T;
}
