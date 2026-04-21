import { expect, test, type Page } from "@playwright/test";

import {
  ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
  API_BASE_URL,
  AUTH_SESSION_ID_STORAGE_KEY,
  AUTH_TOKEN_STORAGE_KEY,
  ensureWorkbenchReady,
  REFRESH_TOKEN_STORAGE_KEY,
  registerViaApi,
  runTaskToDone,
  seedBrowserAuth,
} from "./helpers/workbench";

async function openInspectorContextTab(page: Page): Promise<void> {
  const contextTab = page.getByTestId("inspector-tab-context");
  const contextPanel = page.locator("#inspector-panel-context");
  await expect(contextTab).toBeVisible();
  for (let i = 0; i < 4; i += 1) {
    await contextTab.click();
    if (await contextPanel.isVisible().catch(() => false)) {
      return;
    }
    await page.waitForTimeout(120);
  }
  await expect(contextPanel).toBeVisible({ timeout: 10_000 });
}

async function expectToastContains(page: Page, text: string): Promise<void> {
  const toast = page
    .locator(".ant-message-notice-content")
    .filter({ hasText: text })
    .last();
  await expect(toast).toBeVisible({ timeout: 20_000 });
}

test("rag query empty state is visible @smoke", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await openInspectorContextTab(page);

  const uniqueKb = `kb-empty-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  await page.getByTestId("inspector-rag-kb-input").fill(uniqueKb);
  await page.getByTestId("inspector-rag-kb-apply").click();

  await page
    .getByTestId("inspector-rag-query-input")
    .fill(`never-hit-${Date.now()}-${Math.floor(Math.random() * 10_000)}`);
  await page.getByTestId("inspector-rag-query-submit").click();

  const results = page.getByTestId("inspector-rag-query-results");
  await expect(results).toBeVisible({ timeout: 20_000 });
  await expect(results.locator(".memory-query-hit-item")).toHaveCount(0);
  await expect(results.locator(".panel-note.panel-note--muted")).toBeVisible();
});

test("export endpoints return 404 for missing resources @smoke", async ({
  request,
}) => {
  const auth = await registerViaApi(request);
  const headers = {
    Authorization: `Bearer ${auth.access_token}`,
  };
  const missingTaskId = `task-missing-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  const missingSessionId = `session-missing-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;

  const taskJson = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(missingTaskId)}/export/json?download=1`,
    { headers },
  );
  expect(taskJson.status()).toBe(404);

  const sessionMarkdown = await request.get(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(missingSessionId)}/export/markdown?download=1`,
    { headers },
  );
  expect(sessionMarkdown.status()).toBe(404);
});

test("session export supports empty-session payloads", async ({ request }) => {
  const auth = await registerViaApi(request);
  const headers = {
    Authorization: `Bearer ${auth.access_token}`,
  };

  const createSessionResponse = await request.post(`${API_BASE_URL}/api/sessions`, {
    headers,
    data: {},
  });
  expect(createSessionResponse.ok()).toBeTruthy();
  const createdSession = (await createSessionResponse.json()) as { id: string };

  const sessionJson = await request.get(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(createdSession.id)}/export/json`,
    { headers },
  );
  expect(sessionJson.ok()).toBeTruthy();
  const payload = (await sessionJson.json()) as {
    session: { id: string };
    stats: {
      task_count: number;
      message_count: number;
      trace_step_count: number;
      rag_hit_count: number;
    };
    tasks: unknown[];
    messages: unknown[];
  };
  expect(payload.session.id).toBe(createdSession.id);
  expect(payload.stats.task_count).toBe(0);
  expect(payload.stats.message_count).toBe(0);
  expect(payload.stats.trace_step_count).toBe(0);
  expect(payload.stats.rag_hit_count).toBe(0);
  expect(payload.tasks).toHaveLength(0);
  expect(payload.messages).toHaveLength(0);

  const sessionMarkdown = await request.get(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(createdSession.id)}/export/markdown`,
    { headers },
  );
  expect(sessionMarkdown.ok()).toBeTruthy();
  const markdownText = await sessionMarkdown.text();
  expect(markdownText).toContain("## Tasks");
  expect(markdownText).toContain("_No tasks_");
});

test("export endpoints are isolated across users", async ({ request }) => {
  const owner = await registerViaApi(request);
  const outsider = await registerViaApi(request);
  const created = await runTaskToDone(
    request,
    owner.access_token,
    "playwright export ownership isolation",
  );
  const outsiderHeaders = {
    Authorization: `Bearer ${outsider.access_token}`,
  };

  const outsiderTaskJson = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(created.task_id)}/export/json?download=1`,
    { headers: outsiderHeaders },
  );
  expect(outsiderTaskJson.status()).toBe(404);
  expect(await outsiderTaskJson.text()).toContain("Task not found");

  const outsiderSessionMd = await request.get(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(created.session_id)}/export/markdown?download=1`,
    { headers: outsiderHeaders },
  );
  expect(outsiderSessionMd.status()).toBe(404);
  expect(await outsiderSessionMd.text()).toContain("Session not found");
});

test("task export keeps localized 404 hint when token ownership changes", async ({
  page,
  request,
}) => {
  const owner = await registerViaApi(request);
  const outsider = await registerViaApi(request);
  await seedBrowserAuth(page, owner);

  await page.goto("/");
  await ensureWorkbenchReady(page, owner);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill("playwright export toast 404 mapping");
  await composerSend.click();

  await expect(page.locator(".trace-card").first()).toBeVisible({ timeout: 15_000 });
  await expect(
    page.locator("article.message-row.assistant").filter({
      hasText: "This is a mock response from InsightAgent",
    }).first(),
  ).toBeVisible({ timeout: 20_000 });

  await openInspectorContextTab(page);
  await page.evaluate(
    ({
      accessToken,
      refreshToken,
      authSessionId,
      tokenKey,
      refreshKey,
      authSessionKey,
      activeSessionKey,
    }) => {
      localStorage.setItem(tokenKey, accessToken);
      localStorage.setItem(refreshKey, refreshToken);
      localStorage.setItem(authSessionKey, authSessionId);
      localStorage.removeItem(activeSessionKey);
    },
    {
      accessToken: outsider.access_token,
      refreshToken: outsider.refresh_token,
      authSessionId: outsider.session_id,
      tokenKey: AUTH_TOKEN_STORAGE_KEY,
      refreshKey: REFRESH_TOKEN_STORAGE_KEY,
      authSessionKey: AUTH_SESSION_ID_STORAGE_KEY,
      activeSessionKey: ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
    },
  );

  const exportJsonButton = page.getByTestId("inspector-task-export-json");
  await exportJsonButton.click();
  await expectToastContains(page, "404");
  await expect(exportJsonButton).not.toHaveClass(/ant-btn-loading/, {
    timeout: 10_000,
  });
});
