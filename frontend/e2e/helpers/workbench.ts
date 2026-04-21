import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API_BASE_URL =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";
export const AUTH_TOKEN_STORAGE_KEY = "insightagent.authToken";
export const REFRESH_TOKEN_STORAGE_KEY = "insightagent.refreshToken";
export const AUTH_SESSION_ID_STORAGE_KEY = "insightagent.authSessionId";

export type AuthBootstrapResponse = {
  email: string;
  password: string;
  access_token: string;
  refresh_token: string;
  session_id: string;
};

export async function registerViaApi(
  request: APIRequestContext,
): Promise<AuthBootstrapResponse> {
  const stamp = `${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`;
  const email = `pw-e2e-${stamp}@example.com`;
  const password = "playwright-e2e-123";
  const response = await request.post(`${API_BASE_URL}/api/auth/register`, {
    data: {
      email,
      password,
      display_name: "Playwright E2E",
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = (await response.json()) as Omit<
    AuthBootstrapResponse,
    "email" | "password"
  >;
  return {
    email,
    password,
    ...payload,
  };
}

export async function seedBrowserAuth(
  page: Page,
  auth: Pick<AuthBootstrapResponse, "access_token" | "refresh_token" | "session_id">,
): Promise<void> {
  await page.addInitScript(
    ({
      accessToken,
      refreshToken,
      sessionId,
      authTokenKey,
      refreshTokenKey,
      authSessionKey,
    }) => {
      localStorage.setItem(authTokenKey, accessToken);
      localStorage.setItem(refreshTokenKey, refreshToken);
      localStorage.setItem(authSessionKey, sessionId);
    },
    {
      accessToken: auth.access_token,
      refreshToken: auth.refresh_token,
      sessionId: auth.session_id,
      authTokenKey: AUTH_TOKEN_STORAGE_KEY,
      refreshTokenKey: REFRESH_TOKEN_STORAGE_KEY,
      authSessionKey: AUTH_SESSION_ID_STORAGE_KEY,
    },
  );
}

export async function ensureWorkbenchReady(
  page: Page,
  creds: Pick<AuthBootstrapResponse, "email" | "password">,
): Promise<void> {
  const settingsTrigger = page.getByTestId("sidebar-settings-trigger");
  const emailInput = page.locator("#auth-email");
  const sidebarExpand = page.locator(".sidebar-expand-btn");

  await expect
    .poll(
      async () => {
        if (await settingsTrigger.isVisible().catch(() => false)) {
          return "ready";
        }
        if (await emailInput.isVisible().catch(() => false)) {
          return "auth";
        }
        if (await sidebarExpand.isVisible().catch(() => false)) {
          return "collapsed";
        }
        return "pending";
      },
      { timeout: 20_000, intervals: [500, 1000, 1500, 2000] },
    )
    .not.toBe("pending");

  if (await emailInput.isVisible().catch(() => false)) {
    const passwordInput = page.locator("#auth-password");
    await expect(passwordInput).toBeVisible({ timeout: 15_000 });
    await emailInput.fill(creds.email);
    await passwordInput.fill(creds.password);
    const submitButton = page.locator("button.ant-btn-primary.ant-btn-block");
    await expect(submitButton).toBeVisible({ timeout: 10_000 });
    await submitButton.click();
  }

  if (await sidebarExpand.isVisible().catch(() => false)) {
    await sidebarExpand.click();
  }

  await expect(settingsTrigger).toBeVisible({ timeout: 20_000 });
}
