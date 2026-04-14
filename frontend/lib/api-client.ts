import { AUTH_TOKEN_STORAGE_KEY } from "./storage-keys";

export class ApiError extends Error {
  readonly status: number;
  readonly url: string;
  readonly bodySnippet: string;

  constructor(status: number, message: string, url: string, bodySnippet: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.url = url;
    this.bodySnippet = bodySnippet;
  }
}

function dispatchAuthExpired(url: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent("insightagent:auth-expired", {
      detail: { url },
    }),
  );
}

function readStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    const token = raw?.trim();
    return token ? token : null;
  } catch {
    return null;
  }
}

export function getAuthToken(): string | null {
  return readStoredToken();
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = token.trim();
  if (!normalized) {
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    return;
  }
  localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, normalized);
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

function withAuthHeaders(headers?: HeadersInit): Headers {
  const resolved = new Headers(headers ?? {});
  const token = readStoredToken();
  if (token && !resolved.has("Authorization")) {
    resolved.set("Authorization", `Bearer ${token}`);
  }
  return resolved;
}

export async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const requestUrl = typeof input === "string" ? input : String(input);
  const response = await fetch(input, {
    ...init,
    cache: init?.cache ?? "no-store",
    headers: withAuthHeaders(init?.headers),
  });
  if (
    response.status === 401 &&
    !requestUrl.includes("/api/auth/login") &&
    !requestUrl.includes("/api/auth/register")
  ) {
    dispatchAuthExpired(requestUrl);
  }
  return response;
}

async function readResponse(response: Response, url: string): Promise<string> {
  const text = await response.text();
  if (!response.ok) {
    throw new ApiError(
      response.status,
      `HTTP ${response.status}`,
      url,
      text.slice(0, 280),
    );
  }
  return text;
}

export async function apiJson<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await authFetch(url);
  } catch (cause) {
    const msg =
      cause instanceof TypeError && cause.message.includes("fetch")
        ? "NETWORK"
        : "UNKNOWN";
    throw new ApiError(
      0,
      msg,
      url,
      cause instanceof Error ? cause.message : String(cause),
    );
  }

  const text = await readResponse(response, url);
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, "INVALID_JSON", url, text.slice(0, 120));
  }
}

export async function apiPostJson<T>(url: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await authFetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (cause) {
    throw new ApiError(
      0,
      cause instanceof TypeError ? "NETWORK" : "UNKNOWN",
      url,
      cause instanceof Error ? cause.message : String(cause),
    );
  }

  const text = await readResponse(response, url);
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, "INVALID_JSON", url, text.slice(0, 120));
  }
}

export async function apiPatchJson<T>(url: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await authFetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (cause) {
    throw new ApiError(
      0,
      cause instanceof TypeError ? "NETWORK" : "UNKNOWN",
      url,
      cause instanceof Error ? cause.message : String(cause),
    );
  }

  const text = await readResponse(response, url);
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, "INVALID_JSON", url, text.slice(0, 120));
  }
}

export async function apiPutJson<T>(url: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await authFetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (cause) {
    throw new ApiError(
      0,
      cause instanceof TypeError ? "NETWORK" : "UNKNOWN",
      url,
      cause instanceof Error ? cause.message : String(cause),
    );
  }

  const text = await readResponse(response, url);
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, "INVALID_JSON", url, text.slice(0, 120));
  }
}

export async function apiDelete(url: string): Promise<void> {
  let response: Response;
  try {
    response = await authFetch(url, { method: "DELETE" });
  } catch (cause) {
    throw new ApiError(
      0,
      cause instanceof TypeError ? "NETWORK" : "UNKNOWN",
      url,
      cause instanceof Error ? cause.message : String(cause),
    );
  }
  await readResponse(response, url);
}
