import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API_BASE_URL =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";
const AUTH_TOKEN_STORAGE_KEY = "insightagent.authToken";
const REFRESH_TOKEN_STORAGE_KEY = "insightagent.refreshToken";
const AUTH_SESSION_ID_STORAGE_KEY = "insightagent.authSessionId";

type AuthBootstrapResponse = {
  email: string;
  password: string;
  access_token: string;
  refresh_token: string;
  session_id: string;
};

type TaskCreateResponse = {
  task_id: string;
  session_id: string;
};

async function registerViaApi(
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

async function runTaskToDone(
  request: APIRequestContext,
  token: string,
): Promise<void> {
  const createResponse = await request.post(`${API_BASE_URL}/api/tasks`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      user_input: "playwright usage dashboard visual smoke",
    },
  });
  expect(createResponse.ok()).toBeTruthy();
  const created = (await createResponse.json()) as TaskCreateResponse;
  expect(typeof created.task_id).toBe("string");
  expect(created.task_id.trim().length).toBeGreaterThan(0);

  const streamResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(created.task_id)}/stream`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
  expect(streamResponse.ok()).toBeTruthy();
  const streamText = await streamResponse.text();
  expect(streamText).toContain("event: done");
}

async function waitUsageReady(
  request: APIRequestContext,
  token: string,
): Promise<void> {
  await expect
    .poll(
      async () => {
        const response = await request.get(`${API_BASE_URL}/api/tasks/usage/dashboard`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!response.ok()) {
          return -1;
        }
        const payload = (await response.json()) as {
          summary?: { tasks_with_usage?: number };
        };
        return Number(payload.summary?.tasks_with_usage ?? 0);
      },
      { timeout: 20_000, intervals: [500, 1000, 1500, 2000] },
    )
    .toBeGreaterThan(0);
}

async function seedBrowserAuth(
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

async function ensureWorkbenchReady(
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

test("usage dashboard source trend is visible", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await runTaskToDone(request, auth.access_token);
  await waitUsageReady(request, auth.access_token);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const settingsTrigger = page.getByTestId("sidebar-settings-trigger");
  await expect(settingsTrigger).toBeVisible();
  await settingsTrigger.click();

  const usageEntry = page.getByTestId("settings-menu-usage");
  await expect(usageEntry).toBeVisible();
  await usageEntry.click();

  await expect(page.locator(".usage-dashboard-ant-modal")).toBeVisible();
  await expect(page.locator(".usage-source-trend-block")).toBeVisible();
  await expect(page.locator(".usage-source-trend-row").first()).toBeVisible();
});

test("settings menu governance entries open expected modals", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const settingsTrigger = page.getByTestId("sidebar-settings-trigger");
  await expect(settingsTrigger).toBeVisible();
  await settingsTrigger.click();

  const auditEntry = page.getByTestId("settings-menu-audit");
  await expect(auditEntry).toBeVisible();
  await auditEntry.click();
  await expect(page.locator(".audit-modal")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".audit-modal")).toBeHidden();

  await settingsTrigger.click();
  const knowledgeBaseEntry = page.getByTestId("settings-menu-knowledge-base");
  await expect(knowledgeBaseEntry).toBeVisible();
  await knowledgeBaseEntry.click();
  await expect(page.locator(".knowledge-base-governance-ant-modal")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".knowledge-base-governance-ant-modal")).toBeHidden();

  await settingsTrigger.click();
  const modelEntry = page.getByTestId("settings-menu-model");
  await expect(modelEntry).toBeVisible();
  await modelEntry.click();
  await expect(page.locator(".model-settings-ant-modal")).toBeVisible();
});
