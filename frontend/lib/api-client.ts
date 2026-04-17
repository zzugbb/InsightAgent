import {
  ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
  AUTH_SESSION_ID_STORAGE_KEY,
  AUTH_TOKEN_STORAGE_KEY,
  REFRESH_TOKEN_STORAGE_KEY,
} from "./storage-keys";

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

function readStoredRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
    const token = raw?.trim();
    return token ? token : null;
  } catch {
    return null;
  }
}

export function getAuthToken(): string | null {
  return readStoredToken();
}

export function getRefreshToken(): string | null {
  return readStoredRefreshToken();
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

export function setRefreshToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = token.trim();
  if (!normalized) {
    localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    return;
  }
  localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, normalized);
}

export function setAuthSessionId(sessionId: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  const normalized = sessionId?.trim() ?? "";
  if (!normalized) {
    localStorage.removeItem(AUTH_SESSION_ID_STORAGE_KEY);
    return;
  }
  localStorage.setItem(AUTH_SESSION_ID_STORAGE_KEY, normalized);
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export function clearRefreshToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
}

export function clearAuthSessionStorage(): void {
  clearAuthToken();
  clearRefreshToken();
  if (typeof window === "undefined") {
    return;
  }
  localStorage.removeItem(AUTH_SESSION_ID_STORAGE_KEY);
  localStorage.removeItem(ACTIVE_WORKBENCH_SESSION_STORAGE_KEY);
}

function withAuthHeaders(headers?: HeadersInit): Headers {
  const resolved = new Headers(headers ?? {});
  const token = readStoredToken();
  if (token && !resolved.has("Authorization")) {
    resolved.set("Authorization", `Bearer ${token}`);
  }
  return resolved;
}

function isAuthBootstrapEndpoint(requestUrl: string): boolean {
  return (
    requestUrl.includes("/api/auth/login") ||
    requestUrl.includes("/api/auth/register") ||
    requestUrl.includes("/api/auth/refresh")
  );
}

function resolveRefreshUrl(requestUrl: string): string {
  if (typeof window === "undefined") {
    return "/api/auth/refresh";
  }
  try {
    const parsed = new URL(requestUrl, window.location.origin);
    return `${parsed.origin}/api/auth/refresh`;
  } catch {
    return "/api/auth/refresh";
  }
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefreshAuthSession(requestUrl: string): Promise<boolean> {
  if (refreshInFlight) {
    return refreshInFlight;
  }
  refreshInFlight = (async () => {
    const refreshToken = readStoredRefreshToken();
    if (!refreshToken) {
      return false;
    }
    try {
      const response = await fetch(resolveRefreshUrl(requestUrl), {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        return false;
      }
      const payload = (await response.json()) as {
        access_token?: unknown;
        refresh_token?: unknown;
        session_id?: unknown;
      };
      if (
        typeof payload.access_token !== "string" ||
        typeof payload.refresh_token !== "string"
      ) {
        return false;
      }
      setAuthToken(payload.access_token);
      setRefreshToken(payload.refresh_token);
      setAuthSessionId(
        typeof payload.session_id === "string" ? payload.session_id : null,
      );
      return true;
    } catch {
      return false;
    }
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

export async function authFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const requestUrl = typeof input === "string" ? input : String(input);
  let response = await fetch(input, {
    ...init,
    cache: init?.cache ?? "no-store",
    headers: withAuthHeaders(init?.headers),
  });
  if (response.status !== 401 || isAuthBootstrapEndpoint(requestUrl)) {
    return response;
  }

  const refreshed = await tryRefreshAuthSession(requestUrl);
  if (refreshed) {
    response = await fetch(input, {
      ...init,
      cache: init?.cache ?? "no-store",
      headers: withAuthHeaders(init?.headers),
    });
    if (response.status !== 401) {
      return response;
    }
  }

  clearAuthSessionStorage();
  dispatchAuthExpired(requestUrl);
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
