import { expect, test, type Page } from "@playwright/test";

import {
  API_BASE_URL,
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";

async function openInspectorContextTab(page: Page): Promise<void> {
  const contextTab = page
    .locator(".ant-tabs-tab")
    .filter({ has: page.getByTestId("inspector-tab-context") });
  await expect(contextTab).toBeVisible();
  await contextTab.click();
  await expect(page.locator("#inspector-panel-context")).toBeVisible();
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
