import {
  expect,
  test,
  type APIRequestContext,
  type Locator,
  type Page,
} from "@playwright/test";

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

async function openInspectorContextTab(page: Page): Promise<void> {
  const contextTab = page
    .locator(".ant-tabs-tab")
    .filter({ has: page.getByTestId("inspector-tab-context") });
  await expect(contextTab).toBeVisible();
  await contextTab.click();
  await expect(page.locator("#inspector-panel-context")).toBeVisible();
}

async function triggerDownloadAndAssertName(
  page: Page,
  trigger: Locator,
  expectedPiece: string,
): Promise<void> {
  await expect(trigger).toBeVisible();
  await expect(trigger).toBeEnabled();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    trigger.click(),
  ]);
  expect(download.suggestedFilename().toLowerCase()).toContain(
    expectedPiece.toLowerCase(),
  );
}

test("workbench main path covers trace, rag and task/session export", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill("playwright workbench main path");
  await composerSend.click();

  await expect(page.locator(".trace-card").first()).toBeVisible({ timeout: 15_000 });
  await expect(
    page.locator("article.message-row.assistant").filter({
      hasText: "This is a mock response from InsightAgent",
    }).first(),
  ).toBeVisible({ timeout: 20_000 });

  await openInspectorContextTab(page);

  await triggerDownloadAndAssertName(
    page,
    page.getByTestId("inspector-task-export-json"),
    "task",
  );
  await triggerDownloadAndAssertName(
    page,
    page.getByTestId("inspector-task-export-markdown"),
    "task",
  );
  await triggerDownloadAndAssertName(
    page,
    page.getByTestId("inspector-session-export-json"),
    "session",
  );
  await triggerDownloadAndAssertName(
    page,
    page.getByTestId("inspector-session-export-markdown"),
    "session",
  );

  const ragSnippet = `insightagent-rag-e2e-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  await page.getByTestId("inspector-rag-ingest-input").fill(
    `Knowledge snippet for e2e query: ${ragSnippet}`,
  );
  await page.getByTestId("inspector-rag-ingest-source").fill("playwright-e2e");
  await page.getByTestId("inspector-rag-ingest-submit").click();

  await page.getByTestId("inspector-rag-query-input").fill(ragSnippet);
  await page.getByTestId("inspector-rag-query-submit").click();
  await expect(page.getByTestId("inspector-rag-query-results")).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.locator(".memory-query-hit-doc").first()).toContainText(ragSnippet);
});

test("running task can recover after reload and be cancelled", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  const longPrompt = `[mock-slow-ms=30] cancel-recovery ${"stream ".repeat(260)}`;

  await composerInput.fill(longPrompt);
  await composerSend.click();

  await openInspectorContextTab(page);
  const cancelButton = page.locator('[data-testid="inspector-task-cancel"]:visible').first();
  await expect(cancelButton).toBeVisible({ timeout: 20_000 });

  await page.reload();
  await ensureWorkbenchReady(page, auth);
  await openInspectorContextTab(page);
  const recoveredCancelButton = page
    .locator('[data-testid="inspector-task-cancel"]:visible')
    .first();
  await expect(recoveredCancelButton).toBeVisible({ timeout: 20_000 });
  await recoveredCancelButton.click();

  await expect(recoveredCancelButton).toBeHidden({ timeout: 20_000 });
  await composerInput.fill("post-cancel send still works");
  await expect(composerSend).toBeEnabled({ timeout: 20_000 });
  await composerSend.click();
  await expect(page.locator(".trace-card").first()).toBeVisible({ timeout: 20_000 });
});
