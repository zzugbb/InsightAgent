"use client";

import { ApiError, authFetch } from "./api-client";

export function parseAttachmentFilename(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]).trim() || fallback;
    } catch {
      return utf8Match[1].trim() || fallback;
    }
  }
  const plainMatch = value.match(/filename="?([^";]+)"?/i);
  if (!plainMatch?.[1]) {
    return fallback;
  }
  const normalized = plainMatch[1].trim();
  return normalized || fallback;
}

export function triggerDownload(filename: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function fetchExportResponse(url: string): Promise<Response> {
  let response: Response;
  try {
    response = await authFetch(url, { cache: "no-store" });
  } catch (cause) {
    throw new ApiError(
      0,
      cause instanceof TypeError ? "NETWORK" : "UNKNOWN",
      url,
      cause instanceof Error ? cause.message : String(cause),
    );
  }
  if (response.ok) {
    return response;
  }
  const detail = await response.text();
  throw new ApiError(response.status, `HTTP ${response.status}`, url, detail.slice(0, 280));
}

export async function downloadAuthenticatedExport(
  url: string,
  fallbackFilename: string,
): Promise<string> {
  const response = await fetchExportResponse(url);
  const filename = parseAttachmentFilename(
    response.headers.get("content-disposition"),
    fallbackFilename,
  );
  const blob = await response.blob();
  triggerDownload(filename, blob);
  return filename;
}
