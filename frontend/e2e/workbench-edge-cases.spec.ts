import { expect, test, type Locator, type Page } from "@playwright/test";

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
  const contextTab = page
    .locator(".inspector-ant-tabs .ant-tabs-nav [role='tab']")
    .filter({ hasText: /^(Context|上下文)$/ })
    .first();
  const contextPanel = page.locator("#inspector-panel-context");
  await expect(contextTab).toBeVisible();
  for (let i = 0; i < 4; i += 1) {
    await contextTab.click();
    const ariaSelected = await contextTab.getAttribute("aria-selected");
    const isActive = ariaSelected === "true";
    if (isActive && (await contextPanel.isVisible().catch(() => false))) {
      return;
    }
    await page.waitForTimeout(120);
  }
  await expect
    .poll(
      async () => {
        const ariaSelected = await contextTab.getAttribute("aria-selected");
        const isActive = ariaSelected === "true";
        const panelVisible = await contextPanel.isVisible().catch(() => false);
        return isActive && panelVisible;
      },
      { timeout: 10_000, intervals: [200, 400, 800, 1200] },
    )
    .toBeTruthy();
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

async function expectToastContains(page: Page, text: string): Promise<void> {
  const toast = page
    .locator(".ant-message-notice-content")
    .filter({ hasText: text })
    .last();
  await expect(toast).toBeVisible({ timeout: 20_000 });
}

async function createSessionWithTitle(
  request: Parameters<typeof registerViaApi>[0],
  token: string,
  title: string,
): Promise<string> {
  const headers = {
    Authorization: `Bearer ${token}`,
  };
  const createResponse = await request.post(`${API_BASE_URL}/api/sessions`, {
    headers,
    data: {},
  });
  expect(createResponse.ok()).toBeTruthy();
  const created = (await createResponse.json()) as { id: string };

  const renameResponse = await request.patch(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(created.id)}`,
    {
      headers,
      data: { title },
    },
  );
  expect(renameResponse.ok()).toBeTruthy();
  return created.id;
}

async function selectSessionByTitle(page: Page, title: string): Promise<void> {
  const row = page
    .locator("button.sidebar-item.sidebar-item--single")
    .filter({ hasText: title })
    .first();
  await expect(row).toBeVisible({ timeout: 20_000 });
  const matchesActiveSession = async (): Promise<boolean> => {
    const current = await row.getAttribute("aria-current");
    const titleText = (await page.locator(".chat-title-text").first().textContent()) ?? "";
    return current === "true" && titleText.includes(title);
  };
  for (let i = 0; i < 5; i += 1) {
    await row.click();
    if (await matchesActiveSession()) {
      return;
    }
    await page.waitForTimeout(150);
  }
  let stableHits = 0;
  await expect
    .poll(async () => {
      const matched = await matchesActiveSession();
      if (matched) {
        stableHits += 1;
      } else {
        stableHits = 0;
      }
      return stableHits >= 2;
    }, { timeout: 20_000, intervals: [300, 600, 1200] })
    .toBeTruthy();
}

async function waitForContextCancelButton(page: Page): Promise<Locator> {
  const cancelButton = page
    .locator('[data-testid="inspector-task-cancel"]:visible')
    .first();
  await expect(cancelButton).toBeVisible({ timeout: 20_000 });
  return cancelButton;
}

async function openTaskDetailFromTaskCenter(page: Page): Promise<void> {
  const openTaskCenter = page.getByTestId("chat-open-task-center");
  await expect(openTaskCenter).toBeVisible({ timeout: 20_000 });
  await openTaskCenter.click();
  await expect(page.getByTestId("task-center-shell")).toBeVisible({
    timeout: 20_000,
  });
  const openDetail = page.getByTestId("task-center-open-task-detail").first();
  await expect(openDetail).toBeVisible({ timeout: 20_000 });
  await openDetail.click();
  await expect(page.getByTestId("task-detail-page")).toBeVisible({
    timeout: 20_000,
  });
}

async function waitForRunningTaskIdInSession(args: {
  request: Parameters<typeof registerViaApi>[0];
  token: string;
  sessionId?: string;
  excludeTaskIds?: string[];
}): Promise<string> {
  const excluded = new Set(args.excludeTaskIds ?? []);
  let lastSeenTaskId = "";
  await expect
    .poll(
      async () => {
        const query = args.sessionId
          ? `?limit=20&offset=0&session_id=${encodeURIComponent(args.sessionId)}`
          : "?limit=20&offset=0";
        const response = await args.request.get(
          `${API_BASE_URL}/api/tasks${query}`,
          {
            headers: {
              Authorization: `Bearer ${args.token}`,
            },
          },
        );
        if (!response.ok()) {
          return "";
        }
        const payload = (await response.json()) as {
          items?: Array<{
            id: string;
            status?: string;
            status_normalized?: string;
          }>;
        };
        for (const item of payload.items ?? []) {
          const id = String(item.id ?? "").trim();
          if (!id || excluded.has(id)) {
            continue;
          }
          const normalized = String(item.status_normalized ?? item.status ?? "")
            .trim()
            .toLowerCase();
          lastSeenTaskId = id;
          if (normalized === "pending" || normalized === "running") {
            return id;
          }
        }
        return "";
      },
      { timeout: 20_000, intervals: [300, 600, 1000, 1500] },
    )
    .not.toBe("");
  return lastSeenTaskId;
}

async function createRunningTaskInSession(args: {
  request: Parameters<typeof registerViaApi>[0];
  token: string;
  sessionId: string;
  prompt: string;
}): Promise<{ task_id: string; session_id: string }> {
  const headers = {
    Authorization: `Bearer ${args.token}`,
  };
  const createResponse = await args.request.post(`${API_BASE_URL}/api/tasks`, {
    headers,
    data: {
      user_input: args.prompt,
      session_id: args.sessionId,
    },
  });
  expect(createResponse.ok()).toBeTruthy();
  const created = (await createResponse.json()) as {
    task_id: string;
    session_id: string;
  };

  await expect
    .poll(async () => {
      const response = await args.request.get(
        `${API_BASE_URL}/api/tasks?limit=20&offset=0&session_id=${encodeURIComponent(args.sessionId)}`,
        { headers },
      );
      if (!response.ok()) {
        return "missing";
      }
      const payload = (await response.json()) as {
        items?: Array<{
          id: string;
          status?: string;
          status_normalized?: string;
        }>;
      };
      const found = payload.items?.find((item) => item.id === created.task_id);
      if (!found) {
        return "missing";
      }
      return String(found.status_normalized ?? found.status ?? "")
        .trim()
        .toLowerCase();
    }, { timeout: 15_000, intervals: [300, 700, 1200] })
    .toMatch(/pending|running/);

  return created;
}

test("rag query empty state is visible @smoke", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await openRuntimeDebugModal(page);

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

  await openTaskDetailFromTaskCenter(page);
  await expect(page.getByTestId("task-detail-export-json")).toBeEnabled({
    timeout: 20_000,
  });
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

  const exportJsonButton = page.getByTestId("task-detail-export-json");
  await exportJsonButton.click();
  await expectToastContains(page, "404");
  await expect
    .poll(async () => {
      const count = await exportJsonButton.count();
      if (count === 0) {
        return true;
      }
      const klass = (await exportJsonButton.first().getAttribute("class")) ?? "";
      return !klass.includes("ant-btn-loading");
    }, { timeout: 10_000, intervals: [200, 400, 800, 1200] })
    .toBeTruthy();
});

test("cross-session switch keeps cancel and export scoped to active session", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const sessionATitle = `pw-session-a-${Date.now()}`;
  const sessionBTitle = `pw-session-b-${Date.now()}`;
  await createSessionWithTitle(request, auth.access_token, sessionATitle);
  await createSessionWithTitle(request, auth.access_token, sessionBTitle);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  await selectSessionByTitle(page, sessionATitle);
  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill(`[mock-slow-ms=45] cross-session ${"stream ".repeat(220)}`);
  await composerSend.click();

  await openInspectorContextTab(page);
  const cancelButton = page.locator('[data-testid="inspector-task-cancel"]:visible').first();
  await expect(cancelButton).toBeVisible({ timeout: 20_000 });

  await selectSessionByTitle(page, sessionBTitle);
  await openInspectorContextTab(page);

  await expect(
    page.locator('[data-testid="inspector-task-cancel"]:visible'),
  ).toHaveCount(0);
  await expect(composerSend).not.toHaveClass(/ant-btn-loading/, {
    timeout: 20_000,
  });
  await composerInput.fill("session b still can send");
  await expect(composerSend).toBeEnabled({ timeout: 20_000 });
});

test("cancel allows immediate resend with identical prompt without dedupe loss", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  const samePrompt = `[mock-slow-ms=80] duplicate-visible ${"stream ".repeat(240)}`;

  await composerInput.fill(samePrompt);
  await composerSend.click();

  const firstTaskId = await waitForRunningTaskIdInSession({
    request,
    token: auth.access_token,
  });
  const firstCancelResponse = await request.post(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(firstTaskId)}/cancel`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(firstCancelResponse.ok()).toBeTruthy();

  await expect(composerSend).not.toHaveClass(/ant-btn-loading/, {
    timeout: 8_000,
  });
  await composerInput.fill(samePrompt);
  await expect(composerSend).toBeEnabled({ timeout: 8_000 });
  await composerSend.click();
  const duplicatedUserRows = page
    .locator("article.message-row.user")
    .filter({ hasText: samePrompt });
  await expect
    .poll(async () => duplicatedUserRows.count(), {
      timeout: 10_000,
      intervals: [300, 600, 1000],
    })
    .toBeGreaterThanOrEqual(2);
});

test("streaming state stays scoped when switching sessions and resumes on return", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const sessionATitle = `pw-stream-a-${Date.now()}`;
  const sessionBTitle = `pw-stream-b-${Date.now()}`;
  await createSessionWithTitle(request, auth.access_token, sessionATitle);
  await createSessionWithTitle(request, auth.access_token, sessionBTitle);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await selectSessionByTitle(page, sessionATitle);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill(`[mock-slow-ms=95] scoped-stream ${"stream ".repeat(480)}`);
  await composerSend.click();

  await expect(page.locator("article.message-row.assistant.live")).toBeVisible({
    timeout: 20_000,
  });

  await selectSessionByTitle(page, sessionBTitle);
  await expect(page.locator("article.message-row.assistant.live")).toHaveCount(0);
  await expect(composerSend).not.toHaveClass(/ant-btn-loading/, {
    timeout: 10_000,
  });
  await composerInput.fill("session b still can send while other session streams");
  await expect(composerSend).toBeEnabled({ timeout: 10_000 });

  await selectSessionByTitle(page, sessionATitle);
  await openInspectorContextTab(page);
  const recoveredCancel = await waitForContextCancelButton(page);
  await recoveredCancel.click();
  await expect(composerSend).toBeEnabled({ timeout: 10_000 });
});

test("mock cancel does not show retry affordance and send recovers quickly", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill(`[mock-slow-ms=75] cancel-no-retry ${"stream ".repeat(260)}`);
  await composerSend.click();

  await openInspectorContextTab(page);
  const cancelButton = await waitForContextCancelButton(page);
  await cancelButton.click();

  await expect(composerSend).not.toHaveClass(/ant-btn-loading/, {
    timeout: 4_000,
  });
  await expect(page.locator(".composer-retry")).toHaveCount(0);
  await expect(page.getByTestId("composer-hint")).not.toHaveClass(
    /composer-hint--error/,
  );

  await composerInput.fill("post-cancel still sends in mock mode");
  await expect(composerSend).toBeEnabled({ timeout: 8_000 });
  await composerSend.click();
  await expect(page.locator(".trace-card").first()).toBeVisible({ timeout: 20_000 });
});

test("running task recovery notice covers info to success states", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const sessionTitle = `pw-recovery-success-${Date.now()}`;
  const sessionId = await createSessionWithTitle(request, auth.access_token, sessionTitle);
  await createRunningTaskInSession({
    request,
    token: auth.access_token,
    sessionId,
    prompt: `[mock-slow-ms=35] recovery-success ${"stream ".repeat(520)}`,
  });
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await selectSessionByTitle(page, sessionTitle);

  const recoveryNotice = page.getByTestId("chat-recovery-notice");
  await expect(recoveryNotice).toBeVisible({ timeout: 20_000 });
  await expect(recoveryNotice).toHaveClass(/ant-alert-info/);
  await expect(recoveryNotice).toHaveClass(/ant-alert-success/, {
    timeout: 35_000,
  });
});

test("running task recovery notice shows error when reconnect stream fails", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const sessionTitle = `pw-recovery-failed-${Date.now()}`;
  const sessionId = await createSessionWithTitle(request, auth.access_token, sessionTitle);
  const runningTask = await createRunningTaskInSession({
    request,
    token: auth.access_token,
    sessionId,
    prompt: `[mock-slow-ms=90] recovery-failed ${"stream ".repeat(1200)}`,
  });
  await seedBrowserAuth(page, auth);

  await page.route(
    `**/api/tasks/${runningTask.task_id}/stream?after_seq=*`,
    async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json; charset=utf-8",
        body: JSON.stringify({ detail: "playwright forced resume failure" }),
      });
    },
  );

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await selectSessionByTitle(page, sessionTitle);

  const recoveryNotice = page.getByTestId("chat-recovery-notice");
  await expect(recoveryNotice).toBeVisible({ timeout: 20_000 });
  await expect(recoveryNotice).toHaveClass(/ant-alert-error/, {
    timeout: 20_000,
  });
});

test("trace delta sync retries, pauses in background, and resumes when foreground returns", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  let deltaCallCount = 0;
  await page.route("**/api/tasks/*/trace/delta?*", async (route) => {
    deltaCallCount += 1;
    if (deltaCallCount <= 2) {
      await route.fulfill({
        status: 500,
        contentType: "application/json; charset=utf-8",
        body: JSON.stringify({ detail: "playwright forced delta retry" }),
      });
      return;
    }
    await route.continue();
  });

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill(`[mock-slow-ms=120] delta-pause-resume ${"stream ".repeat(1300)}`);
  await composerSend.click();

  await openInspectorContextTab(page);

  const traceSyncStatus = page.getByTestId("inspector-trace-sync-status");
  await expect
    .poll(async () => (await traceSyncStatus.textContent()) ?? "", {
      timeout: 20_000,
      intervals: [400, 800, 1200],
    })
    .toMatch(/重试|Retry/i);
  await expect(page.getByTestId("inspector-trace-sync-retry-eta")).toBeVisible();

  await expect
    .poll(async () => (await traceSyncStatus.textContent()) ?? "", {
      timeout: 35_000,
      intervals: [500, 900, 1400],
    })
    .toMatch(/正常|Healthy|OK/i);
  await expect(page.getByTestId("inspector-trace-sync-recovered")).toBeVisible();

  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("insightagent:test-page-visibility", {
        detail: { visible: false },
      }),
    );
  });
  await expect
    .poll(async () => (await traceSyncStatus.textContent()) ?? "", {
      timeout: 15_000,
      intervals: [500, 900, 1300],
    })
    .toMatch(/暂停|Paused/i);

  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("insightagent:test-page-visibility", {
        detail: { visible: true },
      }),
    );
  });
  await expect
    .poll(async () => (await traceSyncStatus.textContent()) ?? "", {
      timeout: 20_000,
      intervals: [500, 900, 1300],
    })
    .not.toMatch(/暂停|Paused/i);

  const cancelButton = await waitForContextCancelButton(page);
  await cancelButton.click();
  await expect(composerSend).not.toHaveClass(/ant-btn-loading/, {
    timeout: 8_000,
  });
});

test("auth refresh rotates token and keeps session, logout-all forces relogin", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const settingsTrigger = page.getByTestId("sidebar-settings-trigger");
  await expect(settingsTrigger).toBeVisible();
  const newSessionButton = page.locator("button.sidebar-new-session").first();

  await page.evaluate(({ tokenKey }) => {
    localStorage.setItem(tokenKey, "playwright-invalid-access-token");
  }, { tokenKey: AUTH_TOKEN_STORAGE_KEY });
  const refreshResponsePromise = page.waitForResponse((response) =>
    response.url().includes("/api/auth/refresh"),
  );
  await newSessionButton.click();
  const refreshResponse = await refreshResponsePromise;
  expect(refreshResponse.ok()).toBeTruthy();
  await expect(newSessionButton).not.toHaveClass(/ant-btn-loading/, {
    timeout: 10_000,
  });

  const emailInput = page.locator("#auth-email");
  await expect
    .poll(async () => {
      if (await settingsTrigger.isVisible().catch(() => false)) {
        return "workbench";
      }
      if (await emailInput.isVisible().catch(() => false)) {
        return "auth";
      }
      return "pending";
    }, { timeout: 20_000, intervals: [400, 800, 1200] })
    .toBe("workbench");
  const refreshedToken = await page.evaluate((tokenKey) => {
    return localStorage.getItem(tokenKey);
  }, AUTH_TOKEN_STORAGE_KEY);
  expect(refreshedToken).toBeTruthy();
  expect(refreshedToken).not.toBe("playwright-invalid-access-token");

  const logoutAllResponse = await request.post(`${API_BASE_URL}/api/auth/logout-all`, {
    headers: {
      Authorization: `Bearer ${refreshedToken}`,
    },
  });
  expect(logoutAllResponse.ok()).toBeTruthy();

  await page.evaluate(({ tokenKey }) => {
    localStorage.setItem(tokenKey, "playwright-expired-after-logout-all");
  }, { tokenKey: AUTH_TOKEN_STORAGE_KEY });
  const refreshFailedPromise = page.waitForResponse((response) =>
    response.url().includes("/api/auth/refresh"),
  );
  await newSessionButton.click();
  const refreshFailed = await refreshFailedPromise;
  expect(refreshFailed.status()).toBe(401);

  await expect(emailInput).toBeVisible({ timeout: 20_000 });
  await expect(settingsTrigger).toHaveCount(0);
  const authState = await page.evaluate(
    ({ tokenKey, refreshKey, sessionKey }) => ({
      token: localStorage.getItem(tokenKey),
      refresh: localStorage.getItem(refreshKey),
      session: localStorage.getItem(sessionKey),
    }),
    {
      tokenKey: AUTH_TOKEN_STORAGE_KEY,
      refreshKey: REFRESH_TOKEN_STORAGE_KEY,
      sessionKey: AUTH_SESSION_ID_STORAGE_KEY,
    },
  );
  expect(authState.token).toBeNull();
  expect(authState.refresh).toBeNull();
  expect(authState.session).toBeNull();
});
