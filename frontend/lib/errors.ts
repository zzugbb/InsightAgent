import { ApiError } from "./api-client";
import type { Messages } from "./i18n/types";

export type UserFacingError = {
  banner: string;
  hint?: string;
};

export function toUserFacingError(
  error: unknown,
  err: Messages["errors"],
): UserFacingError {
  if (error instanceof ApiError) {
    if (error.status === 0) {
      if (error.message === "NETWORK") {
        return {
          banner: err.networkBanner,
          hint: err.networkHint,
        };
      }
      return {
        banner: err.unknownBanner,
        hint: error.bodySnippet || undefined,
      };
    }
    if (error.status === 404) {
      return { banner: err.notFound };
    }
    if (error.status === 401 || error.status === 403) {
      return { banner: err.auth };
    }
    if (error.status >= 500) {
      return {
        banner: err.server,
        hint: err.checkBackend,
      };
    }
    return {
      banner: `${err.requestFailed}（${error.status}）`,
      hint: error.bodySnippet || undefined,
    };
  }
  if (error instanceof Error) {
    return { banner: error.message };
  }
  return { banner: err.unknownBanner };
}
