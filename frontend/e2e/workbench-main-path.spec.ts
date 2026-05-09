import {
  expect,
  test,
  type APIRequestContext,
  type Locator,
  type Page,
} from "@playwright/test";

import {
  ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
  API_BASE_URL,
  ensureWorkbenchReady,
  registerViaApi,
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

function expectExportResponseHeaders(args: {
  headers: Record<string, string>;
  contentTypePrefix: string;
  expectedExtension: ".json" | ".md";
}): void {
  const contentType = args.headers["content-type"] ?? "";
  expect(contentType.toLowerCase()).toContain(args.contentTypePrefix.toLowerCase());
  const contentDisposition = args.headers["content-disposition"] ?? "";
  expect(contentDisposition.toLowerCase()).toContain("attachment;");
  expect(contentDisposition.toLowerCase()).toContain(args.expectedExtension);
}

async function triggerDownloadAndAssertName(
  page: Page,
  trigger: Locator,
  expectedPiece: string,
  expectedExtension: ".json" | ".md",
): Promise<string> {
  await expect(trigger).toBeVisible();
  await expect(trigger).toBeEnabled();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    trigger.click(),
  ]);
  const suggestedFilename = download.suggestedFilename().toLowerCase();
  expect(suggestedFilename).toContain(expectedPiece.toLowerCase());
  expect(suggestedFilename).toContain(expectedExtension);
  return suggestedFilename;
}

async function triggerDownloadAndAssertHeaders(args: {
  page: Page;
  trigger: Locator;
  expectedPiece: string;
  expectedExtension: ".json" | ".md";
  request: APIRequestContext;
  token: string;
  requestUrl: string;
  contentTypePrefix: string;
}): Promise<void> {
  await triggerDownloadAndAssertName(
    args.page,
    args.trigger,
    args.expectedPiece,
    args.expectedExtension,
  );

  const response = await args.request.get(args.requestUrl, {
    headers: {
      Authorization: `Bearer ${args.token}`,
    },
  });
  expect(response.ok()).toBeTruthy();
  expectExportResponseHeaders({
    headers: response.headers(),
    contentTypePrefix: args.contentTypePrefix,
    expectedExtension: args.expectedExtension,
  });
}

async function openRuntimeDebugModal(page: Page): Promise<void> {
  const settingsTrigger = page.getByTestId("sidebar-settings-trigger");
  await expect(settingsTrigger).toBeVisible({ timeout: 20_000 });
  await settingsTrigger.click();
  const runtimeEntry = page.getByTestId("settings-menu-runtime-debug");
  await expect(runtimeEntry).toBeVisible({ timeout: 10_000 });
  await runtimeEntry.click();
  await expect(page.getByRole("dialog", { name: /Runtime debug|运行调试/ })).toBeVisible({
    timeout: 20_000,
  });
}

async function closeRuntimeDebugModal(page: Page): Promise<void> {
  const dialog = page.getByRole("dialog", { name: /Runtime debug|运行调试/ });
  await expect(dialog).toBeVisible({ timeout: 10_000 });
  await dialog.locator("button.ant-modal-close").first().click();
  await expect(dialog).toBeHidden({ timeout: 20_000 });
}

async function triggerSessionExportAndAssertName(
  page: Page,
  format: "json" | "markdown",
): Promise<Locator> {
  const activeSessionRow = page.locator(".sidebar-session-row.is-active").first();
  await expect(activeSessionRow).toBeVisible({ timeout: 10_000 });
  const actionsButton = activeSessionRow.getByTestId("sidebar-session-more");
  await expect(actionsButton).toBeVisible({ timeout: 10_000 });
  await actionsButton.click();
  return page.getByTestId(
    format === "json"
      ? "sidebar-session-export-json"
      : "sidebar-session-export-markdown",
  );
}

async function queryRagUntilHit(page: Page, snippet: string): Promise<void> {
  const queryInput = page.getByTestId("inspector-rag-query-input");
  const querySubmit = page.getByTestId("inspector-rag-query-submit");
  const queryResults = page.getByTestId("inspector-rag-query-results");
  const hitDoc = page.locator(".memory-query-hit-doc").first();

  for (let i = 0; i < 5; i += 1) {
    await queryInput.fill(snippet);
    await querySubmit.click();
    await expect(queryResults).toBeVisible({ timeout: 20_000 });
    if (await hitDoc.isVisible().catch(() => false)) {
      await expect(hitDoc).toContainText(snippet);
      return;
    }
    await page.waitForTimeout(450);
  }

  await expect(hitDoc).toContainText(snippet, { timeout: 20_000 });
}

async function openTaskCenterAndDetail(page: Page): Promise<Page> {
  const openTaskCenter = page.getByTestId("chat-open-task-center");
  await expect(openTaskCenter).toBeVisible({ timeout: 20_000 });
  await openTaskCenter.click();
  await expect(page.getByTestId("task-center-shell")).toBeVisible({
    timeout: 20_000,
  });

  const openDetailButton = page
    .getByTestId("task-center-open-task-detail")
    .first();
  await expect(openDetailButton).toBeVisible({ timeout: 20_000 });
  const [detailPage] = await Promise.all([
    page.waitForEvent("popup"),
    openDetailButton.click(),
  ]);
  await detailPage.waitForLoadState("domcontentloaded");
  await expect(detailPage.getByTestId("task-detail-page")).toBeVisible({
    timeout: 20_000,
  });
  return detailPage;
}

async function waitForSessionRunningTask(
  request: APIRequestContext,
  token: string,
  sessionId: string,
): Promise<string> {
  let runningTaskId = "";
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `${API_BASE_URL}/api/tasks?limit=20&offset=0&session_id=${encodeURIComponent(sessionId)}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );
        if (!response.ok()) {
          runningTaskId = "";
          return runningTaskId;
        }
        const payload = (await response.json()) as {
          items?: Array<{ id: string; status: string; status_normalized?: string }>;
        };
        const runningTask = (payload.items ?? []).find((task) => {
          const normalized = (task.status_normalized ?? task.status ?? "")
            .trim()
            .toLowerCase();
          return normalized === "pending" || normalized === "running";
        });
        runningTaskId = runningTask?.id ?? "";
        return runningTaskId;
      },
      { timeout: 20_000, intervals: [300, 600, 1000, 1600] },
    )
    .not.toBe("");
  return runningTaskId;
}

async function waitForContextCancelButton(page: Page): Promise<Locator> {
  const contextTab = page.getByTestId("inspector-tab-context");
  const cancelButton = page
    .locator('[data-testid="inspector-task-cancel"]:visible')
    .first();

  await expect
    .poll(
      async () => {
        if (await cancelButton.isVisible().catch(() => false)) {
          return true;
        }
        if (await contextTab.isVisible().catch(() => false)) {
          await contextTab.click();
        }
        return cancelButton.isVisible().catch(() => false);
      },
      { timeout: 30_000, intervals: [250, 500, 900, 1300] },
    )
    .toBeTruthy();

  return cancelButton;
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

  const activeSessionId = await page.evaluate((activeSessionStorageKey) => {
    return localStorage.getItem(activeSessionStorageKey) ?? "";
  }, ACTIVE_WORKBENCH_SESSION_STORAGE_KEY);
  expect(activeSessionId).not.toBe("");

  const sessionJsonTrigger = await triggerSessionExportAndAssertName(page, "json");
  await triggerDownloadAndAssertHeaders({
    page,
    trigger: sessionJsonTrigger,
    expectedPiece: "session",
    expectedExtension: ".json",
    request,
    token: auth.access_token,
    requestUrl: `${API_BASE_URL}/api/sessions/${encodeURIComponent(activeSessionId)}/export/json?download=1`,
    contentTypePrefix: "application/json",
  });

  const sessionMarkdownTrigger = await triggerSessionExportAndAssertName(page, "markdown");
  await triggerDownloadAndAssertHeaders({
    page,
    trigger: sessionMarkdownTrigger,
    expectedPiece: "session",
    expectedExtension: ".md",
    request,
    token: auth.access_token,
    requestUrl: `${API_BASE_URL}/api/sessions/${encodeURIComponent(activeSessionId)}/export/markdown?download=1`,
    contentTypePrefix: "text/markdown",
  });

  await openRuntimeDebugModal(page);

  const ragSnippet = `insightagent-rag-e2e-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  await page.getByTestId("inspector-rag-ingest-input").fill(
    `Knowledge snippet for e2e query: ${ragSnippet}`,
  );
  await page.getByTestId("inspector-rag-ingest-source").fill("playwright-e2e");
  await page.getByTestId("inspector-rag-ingest-submit").click();

  await queryRagUntilHit(page, ragSnippet);
  await closeRuntimeDebugModal(page);

  const detailPage = await openTaskCenterAndDetail(page);
  const taskDetailUrl = new URL(detailPage.url());
  const taskId = taskDetailUrl.pathname.split("/").filter(Boolean).at(-1) ?? "";
  expect(taskId).not.toBe("");

  await triggerDownloadAndAssertHeaders({
    page: detailPage,
    trigger: detailPage.getByTestId("task-detail-export-json"),
    expectedPiece: "task",
    expectedExtension: ".json",
    request,
    token: auth.access_token,
    requestUrl: `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/export/json?download=1`,
    contentTypePrefix: "application/json",
  });
  await triggerDownloadAndAssertHeaders({
    page: detailPage,
    trigger: detailPage.getByTestId("task-detail-export-markdown"),
    expectedPiece: "task",
    expectedExtension: ".md",
    request,
    token: auth.access_token,
    requestUrl: `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/export/markdown?download=1`,
    contentTypePrefix: "text/markdown",
  });
});

test("workbench main path keeps shared kb actions disabled for non-admin", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  const sharedKbId = `shared-main-path-${Date.now()}`;
  const privateKbId = `kb-main-path-${Date.now()}`;
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "pw-main-path-user",
        email: auth.email,
        display_name: "Playwright Main Path Non Admin",
        role: "user",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    });
  });
  await page.route("**/api/rag/knowledge-bases", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        knowledge_bases: [
          {
            knowledge_base_id: sharedKbId,
            collection: "kb_shared_main_path_mock",
            document_count: 2,
          },
          {
            knowledge_base_id: privateKbId,
            collection: "kb_private_main_path_mock",
            document_count: 1,
          },
        ],
        knowledge_base_count: 2,
        chroma_url: "http://127.0.0.1:8001",
        chroma_reachable: true,
        error: null,
      }),
    });
  });

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-knowledge-base").click();
  await expect(page.locator(".knowledge-base-governance-ant-modal")).toBeVisible();

  const sharedRow = page.locator("tr", { hasText: sharedKbId });
  await expect(sharedRow).toBeVisible();
  await expect(sharedRow.getByTestId("kb-governance-action-clear")).toBeDisabled();
  await expect(sharedRow.getByTestId("kb-governance-action-delete")).toBeDisabled();

  const privateRow = page.locator("tr", { hasText: privateKbId });
  await expect(privateRow).toBeVisible();
  await expect(privateRow.getByTestId("kb-governance-action-clear")).toBeEnabled();
  await expect(privateRow.getByTestId("kb-governance-action-delete")).toBeEnabled();
});

test("running task can recover after reload and be cancelled", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const createSessionResponse = await request.post(`${API_BASE_URL}/api/sessions`, {
    headers: {
      Authorization: `Bearer ${auth.access_token}`,
    },
    data: {},
  });
  expect(createSessionResponse.ok()).toBeTruthy();
  const createdSession = (await createSessionResponse.json()) as { id: string };
  await seedBrowserAuth(page, auth);
  await page.addInitScript(
    ({ activeSessionId, activeSessionStorageKey }) => {
      localStorage.setItem(activeSessionStorageKey, activeSessionId);
    },
    {
      activeSessionId: createdSession.id,
      activeSessionStorageKey: ACTIVE_WORKBENCH_SESSION_STORAGE_KEY,
    },
  );

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  const longPrompt = `[mock-slow-ms=90] cancel-recovery ${"stream ".repeat(420)}`;

  await composerInput.fill(longPrompt);
  await composerSend.click();
  await waitForSessionRunningTask(request, auth.access_token, createdSession.id);

  await page.reload();
  await ensureWorkbenchReady(page, auth);
  const recoveredCancelButton = await waitForContextCancelButton(page);
  await recoveredCancelButton.click();

  await expect(recoveredCancelButton).toBeHidden({ timeout: 20_000 });
  await composerInput.fill("post-cancel send still works");
  await expect(composerSend).toBeEnabled({ timeout: 20_000 });
  await composerSend.click();
  await expect(page.locator(".trace-card").first()).toBeVisible({ timeout: 20_000 });
});

test("scroll-to-bottom button appears on manual up-scroll and returns to hidden after jump", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  await page.setViewportSize({ width: 1280, height: 560 });

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  const assistantMessages = page.locator("article.message-row.assistant:not(.live)");

  for (let i = 0; i < 3; i += 1) {
    const beforeCount = await assistantMessages.count();
    await composerInput.fill(`seed history ${i} ${"history ".repeat(220)}`);
    await composerSend.click();
    await expect
      .poll(async () => assistantMessages.count(), {
        timeout: 20_000,
        intervals: [500, 1000, 1500, 2000],
      })
      .toBeGreaterThan(beforeCount);
  }

  const messageStage = page.getByTestId("chat-message-stage");
  await expect
    .poll(
      async () =>
        messageStage.evaluate((el) => el.scrollHeight > el.clientHeight + 40),
      { timeout: 20_000, intervals: [400, 800, 1200] },
    )
    .toBeTruthy();
  await messageStage.evaluate((el) => {
    const nextTop = Math.max(0, el.scrollHeight - el.clientHeight - 240);
    el.scrollTop = nextTop;
    el.dispatchEvent(new Event("scroll", { bubbles: true }));
  });
  await expect
    .poll(
      async () =>
        messageStage.evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight),
      { timeout: 20_000, intervals: [200, 500, 1000] },
    )
    .toBeGreaterThan(120);

  const scrollFab = page.getByTestId("chat-scroll-fab");
  await expect(scrollFab).toBeVisible({ timeout: 20_000 });

  await scrollFab.click();
  await expect(scrollFab).toBeHidden({ timeout: 20_000 });
});
