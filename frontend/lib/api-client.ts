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
    response = await fetch(url, { cache: "no-store" });
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
    response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
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
    response = await fetch(url, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
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
    response = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
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
    response = await fetch(url, { method: "DELETE", cache: "no-store" });
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
