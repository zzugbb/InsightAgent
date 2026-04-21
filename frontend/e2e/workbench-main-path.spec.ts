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

  await queryRagUntilHit(page, ragSnippet);
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
