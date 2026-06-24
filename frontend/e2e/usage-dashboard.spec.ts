import { expect, test, type Locator, type Page } from "@playwright/test";

import {
  API_BASE_URL,
  ensureWorkbenchReady,
  ingestKnowledgeSnippet,
  registerViaApi,
  runTaskToDone,
  seedBrowserAuth,
  waitUsageReady,
} from "./helpers/workbench";

async function assertHeadersLeftAligned(headers: Locator): Promise<void> {
  const count = await headers.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i += 1) {
    const align = await headers.nth(i).evaluate((el) => getComputedStyle(el).textAlign);
    expect(["left", "start"]).toContain(align);
  }
}

async function openSettingsMenu(page: Parameters<typeof ensureWorkbenchReady>[0]): Promise<void> {
  const settingsTrigger = page.getByTestId("sidebar-settings-trigger");
  await expect(settingsTrigger).toBeVisible();
  await settingsTrigger.click();
  await expect(page.getByTestId("sidebar-settings-menu-popover")).toBeVisible();
}

function exactText(value: string): RegExp {
  return new RegExp(`^${value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`);
}

async function selectVisibleAntdOption(
  page: Page,
  args: {
    triggerTestId: string;
    value: string;
  },
): Promise<void> {
  await page.getByTestId(args.triggerTestId).click();
  const dropdown = page
    .locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)")
    .last();
  await expect(dropdown).toBeVisible({ timeout: 10_000 });

  const roleOption = dropdown
    .getByRole("option", { name: exactText(args.value), exact: true })
    .last();
  if (await roleOption.isVisible().catch(() => false)) {
    await roleOption.click();
    return;
  }

  const visibleOption = dropdown
    .locator(".ant-select-item-option")
    .filter({ hasText: exactText(args.value) })
    .last();
  if (await visibleOption.isVisible().catch(() => false)) {
    await visibleOption.click();
    return;
  }

  const visibleOptionText = dropdown.getByText(args.value, {
    exact: true,
  }).last();
  await expect(visibleOptionText).toBeVisible({ timeout: 10_000 });
  await visibleOptionText.click();
}

async function getJsonWithRetry(
  request: Parameters<typeof registerViaApi>[0],
  url: string,
  headers: Record<string, string>,
  attempts = 3,
): Promise<unknown> {
  let lastError: unknown;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await request.get(url, { headers });
      expect(response.ok()).toBeTruthy();
      return response.json();
    } catch (error) {
      lastError = error;
      if (attempt < attempts - 1) {
        await new Promise((resolve) => setTimeout(resolve, 500 * (attempt + 1)));
      }
    }
  }
  throw lastError;
}

async function closeModelSettingsModal(page: Page): Promise<void> {
  const modal = page.locator(".model-settings-ant-modal");
  const closeButton = modal.locator(".ant-modal-close").first();
  await expect(closeButton).toBeVisible({ timeout: 10_000 });
  await closeButton.click();
  await expect(modal).toBeHidden({ timeout: 10_000 });
}

async function saveToolRegistryProfile(
  page: Parameters<typeof ensureWorkbenchReady>[0],
  profile: "planning_only" | "retrieval_only" | "calculator_only",
  options?: {
    source?: string;
  },
): Promise<{
  tool_registry_profile?: string;
  tool_registry_provider_source?: string;
  enabled_tool_labels?: string[];
}> {
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-model").click();
  await expect(page.locator(".model-settings-ant-modal")).toBeVisible();

  await selectVisibleAntdOption(page, {
    triggerTestId: "model-settings-tool-registry-profile",
    value: profile,
  });

  if (options?.source) {
    await selectVisibleAntdOption(page, {
      triggerTestId: "model-settings-tool-registry-source",
      value: options.source,
    });
  }

  const saveResponsePromise = page.waitForResponse((response) => {
    return (
      response.url().includes("/api/settings")
      && response.request().method() === "PUT"
    );
  });
  await page.getByTestId("model-settings-save").click();
  const saveResponse = await saveResponsePromise;
  expect(saveResponse.ok()).toBeTruthy();
  const payload = (await saveResponse.json()) as {
    tool_registry_profile?: string;
    tool_registry_provider_source?: string;
    enabled_tool_labels?: string[];
  };

  const metaDescriptions = page.locator(".model-settings-meta-descriptions");
  await expect(metaDescriptions).toContainText(profile);
  for (const label of payload.enabled_tool_labels ?? []) {
    await expect(metaDescriptions).toContainText(label);
  }
  await closeModelSettingsModal(page);
  return payload;
}

async function submitPromptAndCaptureTaskId(
  page: Page,
  prompt: string,
): Promise<string> {
  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill(prompt);
  const createTaskResponsePromise = page.waitForResponse((response) => {
    if (response.request().method() !== "POST") {
      return false;
    }
    try {
      return new URL(response.url()).pathname === "/api/tasks";
    } catch {
      return false;
    }
  });
  await composerSend.click();
  const createTaskResponse = await createTaskResponsePromise;
  expect(createTaskResponse.ok()).toBeTruthy();
  const payload = (await createTaskResponse.json()) as { task_id?: string };
  expect(typeof payload.task_id).toBe("string");
  expect((payload.task_id ?? "").trim().length).toBeGreaterThan(0);
  return String(payload.task_id).trim();
}

async function openTaskDetailFromTaskCenter(
  page: Page,
  taskId: string,
): Promise<Page> {
  const taskCenterShell = page.getByTestId("task-center-shell");
  const openTaskCenter = page.getByTestId("chat-open-task-center");
  if (!(await taskCenterShell.isVisible().catch(() => false))) {
    await expect(openTaskCenter).toBeVisible({ timeout: 20_000 });
    await openTaskCenter.click();
  }
  await expect(taskCenterShell).toBeVisible({
    timeout: 20_000,
  });
  const taskKeywordFilter = page.getByTestId("task-center-keyword-filter");
  await taskKeywordFilter.fill(taskId);
  const openDetailButtons = page.getByTestId("task-center-open-task-detail");
  await expect
    .poll(() => openDetailButtons.count(), {
      timeout: 20_000,
      intervals: [200, 400, 800],
    })
    .toBe(1);
  const openDetail = page.getByTestId("task-center-open-task-detail").first();
  await expect(openDetail).toBeVisible({ timeout: 20_000 });
  const [detailPage] = await Promise.all([
    page.waitForEvent("popup"),
    openDetail.click(),
  ]);
  await detailPage.waitForLoadState("domcontentloaded");
  await expect(detailPage.getByTestId("task-detail-page")).toBeVisible({
    timeout: 20_000,
  });
  return detailPage;
}

async function assertInspectorSessionGovernance(
  page: Page,
  args: {
    profile: string;
    source: string;
    expectedAllowed: string;
    forbiddenAllowed: string[];
  },
): Promise<void> {
  await page.getByTestId("inspector-tab-context").click();
  const governanceSummary = page.getByTestId("inspector-session-governance");
  await expect(governanceSummary).toBeVisible({ timeout: 20_000 });
  await expect(governanceSummary).toContainText(args.profile);
  await expect(governanceSummary).toContainText(args.source);
  await expect(governanceSummary).toContainText(args.expectedAllowed);
  for (const forbidden of args.forbiddenAllowed) {
    await expect(governanceSummary).not.toContainText(forbidden);
  }
}

test("usage dashboard source trend is visible @smoke", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await runTaskToDone(request, auth.access_token, "playwright usage dashboard visual smoke");
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

test("usage dashboard source filter request and table alignments are stable", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await runTaskToDone(request, auth.access_token, "playwright usage dashboard filter assertions");
  await waitUsageReady(request, auth.access_token);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-usage").click();

  const usageModal = page.locator(".usage-dashboard-ant-modal");
  await expect(usageModal).toBeVisible();
  await assertHeadersLeftAligned(
    page.locator('[data-testid="usage-dashboard-table-wrap"] .ant-table-thead > tr > th'),
  );

  const estimatedResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/tasks/usage/dashboard")) {
      return false;
    }
    const url = new URL(response.url());
    return url.searchParams.get("source_kind") === "estimated";
  });
  await page.getByTestId("usage-source-filter-estimated").click();
  await estimatedResponse;
  await expect(page.getByTestId("usage-source-trend-block")).toBeVisible();

  const providerResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/tasks/usage/dashboard")) {
      return false;
    }
    const url = new URL(response.url());
    return url.searchParams.get("source_kind") === "provider";
  });
  await page.getByTestId("usage-source-filter-provider").click();
  await providerResponse;
  await expect(page.getByTestId("usage-source-trend-block")).toBeVisible();
});

test("usage dashboard governance filters drive backend request params", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "planning_only", {
    source: "planning_suite",
  });
  expect(savedPayload.tool_registry_profile).toBe("planning_only");
  expect(savedPayload.tool_registry_provider_source).toBe("planning_suite");

  await runTaskToDone(
    request,
    auth.access_token,
    "usage dashboard governance filter request contract [kb:usage] [calc:2+3]",
  );
  await waitUsageReady(request, auth.access_token);

  await openSettingsMenu(page);
  await page.getByTestId("settings-menu-usage").click();
  await expect(page.locator(".usage-dashboard-ant-modal")).toBeVisible();

  const profileResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/tasks/usage/dashboard")) {
      return false;
    }
    const url = new URL(response.url());
    return url.searchParams.get("tool_registry_profile") === "planning_only";
  });
  await selectVisibleAntdOption(page, {
    triggerTestId: "usage-governance-profile-filter",
    value: "planning_only",
  });
  await profileResponse;

  const sourceResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/tasks/usage/dashboard")) {
      return false;
    }
    const url = new URL(response.url());
    return (
      url.searchParams.get("tool_registry_profile") === "planning_only"
      && url.searchParams.get("tool_registry_provider_source") === "planning_suite"
    );
  });
  await selectVisibleAntdOption(page, {
    triggerTestId: "usage-governance-source-filter",
    value: "planning_suite",
  });
  await sourceResponse;
});

test("task center governance filters drive backend request params", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "planning_only", {
    source: "planning_suite",
  });
  expect(savedPayload.tool_registry_profile).toBe("planning_only");
  expect(savedPayload.tool_registry_provider_source).toBe("planning_suite");

  await runTaskToDone(
    request,
    auth.access_token,
    "task center governance filter request contract [kb:task-center] [calc:6+1]",
  );

  await page.getByTestId("chat-open-task-center").click();
  await expect(page.getByTestId("task-center-shell")).toBeVisible();

  const profileResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/tasks")) {
      return false;
    }
    const url = new URL(response.url());
    return url.searchParams.get("tool_registry_profile") === "planning_only";
  });
  await selectVisibleAntdOption(page, {
    triggerTestId: "task-center-governance-profile-filter",
    value: "planning_only",
  });
  await profileResponse;

  const sourceResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/tasks")) {
      return false;
    }
    const url = new URL(response.url());
    return (
      url.searchParams.get("tool_registry_profile") === "planning_only"
      && url.searchParams.get("tool_registry_provider_source") === "planning_suite"
    );
  });
  await selectVisibleAntdOption(page, {
    triggerTestId: "task-center-governance-source-filter",
    value: "planning_suite",
  });
  await sourceResponse;
});

test("settings menu governance entries open expected modals @smoke", async ({
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
  await assertHeadersLeftAligned(
    page.locator('[data-testid="kb-governance-table-wrap"] .ant-table-thead > tr > th'),
  );
  await expect(page.getByTestId("kb-governance-refresh")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator(".knowledge-base-governance-ant-modal")).toBeHidden();

  await settingsTrigger.click();
  const modelEntry = page.getByTestId("settings-menu-model");
  await expect(modelEntry).toBeVisible();
  await modelEntry.click();
  await expect(page.locator(".model-settings-ant-modal")).toBeVisible();
});

test("model settings validate previews planning-only enabled tools", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-model").click();
  await expect(page.locator(".model-settings-ant-modal")).toBeVisible();

  await selectVisibleAntdOption(page, {
    triggerTestId: "model-settings-tool-registry-profile",
    value: "planning_only",
  });

  const validateResponsePromise = page.waitForResponse((response) => {
    return (
      response.url().includes("/api/settings/validate")
      && response.request().method() === "POST"
    );
  });
  await page.getByTestId("model-settings-validate").click();
  const validateResponse = await validateResponsePromise;
  expect(validateResponse.ok()).toBeTruthy();
  const payload = (await validateResponse.json()) as {
    tool_registry_profile?: string;
    enabled_tool_labels?: string[];
  };
  expect(payload.tool_registry_profile).toBe("planning_only");
  expect(payload.enabled_tool_labels).toEqual(["Task Planner"]);

  const metaDescriptions = page.locator(".model-settings-meta-descriptions");
  await expect(metaDescriptions).toContainText("planning_only");
  await expect(metaDescriptions).toContainText("Task Planner");
});

test("model settings validate previews retrieval suite enabled tools", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-model").click();
  await expect(page.locator(".model-settings-ant-modal")).toBeVisible();

  await selectVisibleAntdOption(page, {
    triggerTestId: "model-settings-tool-registry-profile",
    value: "retrieval_only",
  });
  await selectVisibleAntdOption(page, {
    triggerTestId: "model-settings-tool-registry-source",
    value: "retrieval_suite",
  });

  const validateResponsePromise = page.waitForResponse((response) => {
    return (
      response.url().includes("/api/settings/validate")
      && response.request().method() === "POST"
    );
  });
  await page.getByTestId("model-settings-validate").click();
  const validateResponse = await validateResponsePromise;
  expect(validateResponse.ok()).toBeTruthy();
  const payload = (await validateResponse.json()) as {
    tool_registry_profile?: string;
    tool_registry_provider_source?: string;
    enabled_tool_labels?: string[];
  };
  expect(payload.tool_registry_profile).toBe("retrieval_only");
  expect(payload.tool_registry_provider_source).toBe("retrieval_suite");
  expect(payload.enabled_tool_labels).toEqual(["Knowledge Retrieval Suite"]);

  const metaDescriptions = page.locator(".model-settings-meta-descriptions");
  await expect(metaDescriptions).toContainText("retrieval_only");
  await expect(metaDescriptions).toContainText("retrieval_suite");
  await expect(metaDescriptions).toContainText("Knowledge Retrieval Suite");
  await expect(
    page.getByTestId("model-settings-selected-profile-summary"),
  ).toContainText("Knowledge Retrieval");
  await expect(
    page.getByTestId("model-settings-selected-source-summary"),
  ).toContainText("retrieval_only");
  await expect(
    page.getByTestId("model-settings-selected-source-summary"),
  ).toContainText("Knowledge Retrieval Suite");
});

test("model settings validate previews calculator suite enabled tools", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-model").click();
  await expect(page.locator(".model-settings-ant-modal")).toBeVisible();

  await selectVisibleAntdOption(page, {
    triggerTestId: "model-settings-tool-registry-profile",
    value: "calculator_only",
  });
  await selectVisibleAntdOption(page, {
    triggerTestId: "model-settings-tool-registry-source",
    value: "calculator_suite",
  });

  const validateResponsePromise = page.waitForResponse((response) => {
    return (
      response.url().includes("/api/settings/validate")
      && response.request().method() === "POST"
    );
  });
  await page.getByTestId("model-settings-validate").click();
  const validateResponse = await validateResponsePromise;
  expect(validateResponse.ok()).toBeTruthy();
  const payload = (await validateResponse.json()) as {
    tool_registry_profile?: string;
    tool_registry_provider_source?: string;
    enabled_tool_labels?: string[];
  };
  expect(payload.tool_registry_profile).toBe("calculator_only");
  expect(payload.tool_registry_provider_source).toBe("calculator_suite");
  expect(payload.enabled_tool_labels).toEqual(["Calculator Suite"]);

  const metaDescriptions = page.locator(".model-settings-meta-descriptions");
  await expect(metaDescriptions).toContainText("calculator_only");
  await expect(metaDescriptions).toContainText("calculator_suite");
  await expect(metaDescriptions).toContainText("Calculator Suite");
  await expect(
    page.getByTestId("model-settings-selected-profile-summary"),
  ).toContainText("calc_eval");
  await expect(
    page.getByTestId("model-settings-selected-source-summary"),
  ).toContainText("calculator_only");
  await expect(
    page.getByTestId("model-settings-selected-source-summary"),
  ).toContainText("Calculator Suite");
});

test("saved planning-only profile constrains actual trace allowed tools", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "planning_only");
  expect(savedPayload.tool_registry_profile).toBe("planning_only");
  expect(savedPayload.enabled_tool_labels).toEqual(["Task Planner"]);

  await submitPromptAndCaptureTaskId(
    page,
    "Need rag context and [calc:1+2] for planning-only runtime acceptance",
  );

  const allowedToolsMeta = page
    .getByTestId("trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(allowedToolsMeta).toContainText("Profile planning_only");
  await expect(allowedToolsMeta).toContainText("Source default");
  await expect(allowedToolsMeta).toContainText("Task Planner");
  await expect(allowedToolsMeta).not.toContainText("Knowledge Retrieval");
  await expect(allowedToolsMeta).not.toContainText("calc_eval");

  await expect(
    page.getByTestId("trace-card").filter({ hasText: "Task Planner" }).first(),
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    page.locator("article.message-row.assistant").filter({
      hasText: "This is a mock response from InsightAgent",
    }).first(),
  ).toBeVisible({ timeout: 20_000 });

  const traceFeedText = await page.getByTestId("inspector-trace-feed").textContent();
  expect(traceFeedText ?? "").not.toContain("Knowledge Retrieval");
  expect(traceFeedText ?? "").not.toContain("calc_eval");

  await assertInspectorSessionGovernance(page, {
    profile: "planning_only",
    source: "default",
    expectedAllowed: "Task Planner",
    forbiddenAllowed: ["Knowledge Retrieval", "calc_eval"],
  });
});

test("saved retrieval-only profile executes retrieval without planner or calculator", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "retrieval_only");
  expect(savedPayload.tool_registry_profile).toBe("retrieval_only");
  expect(savedPayload.enabled_tool_labels).toEqual(["Knowledge Retrieval"]);

  await submitPromptAndCaptureTaskId(
    page,
    "Please retrieve project context from the kb and explain the result [kb:demo]",
  );

  const allowedToolsMeta = page
    .getByTestId("trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(allowedToolsMeta).toContainText("Profile retrieval_only");
  await expect(allowedToolsMeta).toContainText("Source default");
  await expect(allowedToolsMeta).toContainText("Knowledge Retrieval");
  await expect(allowedToolsMeta).not.toContainText("Task Planner");
  await expect(allowedToolsMeta).not.toContainText("calc_eval");

  await expect(
    page.getByTestId("trace-card").filter({ hasText: "Knowledge Retrieval" }).first(),
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    page.locator("article.message-row.assistant").filter({
      hasText: "This is a mock response from InsightAgent",
    }).first(),
  ).toBeVisible({ timeout: 20_000 });

  const traceFeedText = await page.getByTestId("inspector-trace-feed").textContent();
  expect(traceFeedText ?? "").toContain("Knowledge Retrieval");
  expect(traceFeedText ?? "").not.toContain("Task Planner");
  expect(traceFeedText ?? "").not.toContain("calc_eval");

  await assertInspectorSessionGovernance(page, {
    profile: "retrieval_only",
    source: "default",
    expectedAllowed: "Knowledge Retrieval",
    forbiddenAllowed: ["Task Planner", "calc_eval"],
  });
});

test("saved calculator-only profile executes calculator without planner or retrieval", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "calculator_only");
  expect(savedPayload.tool_registry_profile).toBe("calculator_only");
  expect(savedPayload.enabled_tool_labels).toEqual(["calc_eval"]);

  await submitPromptAndCaptureTaskId(
    page,
    "Please calculate the result for me [calc:12/3+5]",
  );

  const allowedToolsMeta = page
    .getByTestId("trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(allowedToolsMeta).toContainText("Profile calculator_only");
  await expect(allowedToolsMeta).toContainText("Source default");
  await expect(allowedToolsMeta).toContainText("calc_eval");
  await expect(allowedToolsMeta).not.toContainText("Task Planner");
  await expect(allowedToolsMeta).not.toContainText("Knowledge Retrieval");

  await expect(
    page.getByTestId("trace-card").filter({ hasText: "calc_eval" }).first(),
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    page.locator("article.message-row.assistant").filter({
      hasText: "This is a mock response from InsightAgent",
    }).first(),
  ).toBeVisible({ timeout: 20_000 });

  const traceFeedText = await page.getByTestId("inspector-trace-feed").textContent();
  expect(traceFeedText ?? "").toContain("calc_eval");
  expect(traceFeedText ?? "").not.toContain("Task Planner");
  expect(traceFeedText ?? "").not.toContain("Knowledge Retrieval");

  await assertInspectorSessionGovernance(page, {
    profile: "calculator_only",
    source: "default",
    expectedAllowed: "calc_eval",
    forbiddenAllowed: ["Task Planner", "Knowledge Retrieval"],
  });
});

test("saved planning suite source propagates through runtime and export governance", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "planning_only", {
    source: "planning_suite",
  });
  expect(savedPayload.tool_registry_profile).toBe("planning_only");
  expect(savedPayload.tool_registry_provider_source).toBe("planning_suite");
  expect(savedPayload.enabled_tool_labels).toEqual(["Task Planner Suite"]);

  const taskId = await submitPromptAndCaptureTaskId(
    page,
    "Need planning suite runtime acceptance with rag and calculator requests [kb:suite] [calc:9+3]",
  );

  const allowedToolsMeta = page
    .getByTestId("trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(allowedToolsMeta).toContainText("Profile planning_only");
  await expect(allowedToolsMeta).toContainText("Source planning_suite");
  await expect(allowedToolsMeta).toContainText("Task Planner Suite");
  await expect(allowedToolsMeta).not.toContainText("Knowledge Retrieval");
  await expect(allowedToolsMeta).not.toContainText("calc_eval");

  await assertInspectorSessionGovernance(page, {
    profile: "planning_only",
    source: "planning_suite",
    expectedAllowed: "Task Planner Suite",
    forbiddenAllowed: ["Knowledge Retrieval", "calc_eval"],
  });

  const taskResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(taskResponse.ok()).toBeTruthy();
  const taskPayload = (await taskResponse.json()) as { session_id: string };
  expect(taskPayload.session_id.trim()).not.toBe("");

  const openTaskCenter = page.getByTestId("chat-open-task-center");
  await expect(openTaskCenter).toBeVisible({ timeout: 20_000 });
  await openTaskCenter.click();
  await expect(page.getByTestId("task-center-shell")).toBeVisible({
    timeout: 20_000,
  });
  const taskKeywordFilter = page.getByTestId("task-center-keyword-filter");
  const taskQueryResponsePromise = page.waitForResponse((response) => {
    if (response.request().method() !== "GET") {
      return false;
    }
    try {
      const url = new URL(response.url());
      return (
        url.pathname === "/api/tasks"
        && url.searchParams.get("query") === "planning_suite"
      );
    } catch {
      return false;
    }
  });
  await taskKeywordFilter.fill("planning_suite");
  const taskQueryResponse = await taskQueryResponsePromise;
  expect(taskQueryResponse.ok()).toBeTruthy();
  const taskCenterGovernance = page.getByTestId("task-center-governance-summary");
  await expect
    .poll(() => taskCenterGovernance.count(), {
      timeout: 20_000,
      intervals: [200, 400, 800],
    })
    .toBe(1);
  await expect(taskCenterGovernance.first()).toContainText("planning_only");
  await expect(taskCenterGovernance.first()).toContainText("planning_suite");
  await expect(taskCenterGovernance.first()).toContainText("Task Planner Suite");
  await taskKeywordFilter.fill(taskId);

  const detailPage = await openTaskDetailFromTaskCenter(page, taskId);
  const detailAllowedToolsMeta = detailPage
    .getByTestId("task-detail-trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(detailAllowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(detailAllowedToolsMeta).toContainText("Source planning_suite");
  await expect(detailAllowedToolsMeta).toContainText("Task Planner Suite");
  await expect(detailAllowedToolsMeta).not.toContainText("Knowledge Retrieval");
  await expect(detailAllowedToolsMeta).not.toContainText("calc_eval");

  const governanceSummary = detailPage.getByTestId(
    "task-detail-governance-summary",
  );
  await expect(governanceSummary).toBeVisible({ timeout: 20_000 });
  await expect(governanceSummary).toContainText("planning_only");
  await expect(governanceSummary).toContainText("planning_suite");
  await expect(governanceSummary).toContainText("Task Planner Suite");

  const taskExportJsonResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/export/json`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(taskExportJsonResponse.ok()).toBeTruthy();
  const taskExportJsonPayload = (await taskExportJsonResponse.json()) as {
    trace?: {
      governance?: {
        profile?: string;
        provider_source?: string;
        allowed_tool_labels?: string[];
      };
    };
  };
  expect(taskExportJsonPayload.trace?.governance?.profile).toBe("planning_only");
  expect(taskExportJsonPayload.trace?.governance?.provider_source).toBe(
    "planning_suite",
  );
  expect(taskExportJsonPayload.trace?.governance?.allowed_tool_labels).toEqual([
    "Task Planner Suite",
  ]);

  const sessionExportJsonResponse = await request.get(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(taskPayload.session_id)}/export/json`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(sessionExportJsonResponse.ok()).toBeTruthy();
  const sessionExportJsonPayload = (await sessionExportJsonResponse.json()) as {
    governance?: {
      profiles?: string[];
      provider_sources?: string[];
      allowed_tool_labels?: string[];
    };
  };
  expect(sessionExportJsonPayload.governance?.profiles).toContain("planning_only");
  expect(sessionExportJsonPayload.governance?.provider_sources).toContain(
    "planning_suite",
  );
  expect(sessionExportJsonPayload.governance?.allowed_tool_labels).toContain(
    "Task Planner Suite",
  );

  await waitUsageReady(request, auth.access_token);
  await detailPage.close();
  await page.getByTestId("task-center-close").click();
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-usage").click();
  await expect(page.locator(".usage-dashboard-ant-modal")).toBeVisible();
  const usageSessionGovernance = page.getByTestId("usage-session-governance-summary");
  await expect(usageSessionGovernance.first()).toContainText("planning_only");
  await expect(usageSessionGovernance.first()).toContainText("planning_suite");
  await expect(usageSessionGovernance.first()).toContainText("Task Planner Suite");
  await page
    .locator(".usage-bottom-head .ant-segmented-item")
    .filter({ hasText: "Top tasks" })
    .click();
  const usageTaskGovernance = page.getByTestId("usage-task-governance-summary");
  await expect(usageTaskGovernance.first()).toContainText("planning_only");
  await expect(usageTaskGovernance.first()).toContainText("planning_suite");
  await expect(usageTaskGovernance.first()).toContainText("Task Planner Suite");

  await page.keyboard.press("Escape");
});

test("saved retrieval suite source propagates through runtime and export governance", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "retrieval_only", {
    source: "retrieval_suite",
  });
  expect(savedPayload.tool_registry_profile).toBe("retrieval_only");
  expect(savedPayload.tool_registry_provider_source).toBe("retrieval_suite");
  expect(savedPayload.enabled_tool_labels).toEqual(["Knowledge Retrieval Suite"]);

  const taskId = await submitPromptAndCaptureTaskId(
    page,
    "Retrieve suite runtime acceptance from the selected kb [kb:retrieval-suite-check]",
  );

  const allowedToolsMeta = page
    .getByTestId("trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(allowedToolsMeta).toContainText("Profile retrieval_only");
  await expect(allowedToolsMeta).toContainText("Source retrieval_suite");
  await expect(allowedToolsMeta).toContainText("Knowledge Retrieval Suite");
  await expect(allowedToolsMeta).not.toContainText("Task Planner");
  await expect(allowedToolsMeta).not.toContainText("calc_eval");

  await assertInspectorSessionGovernance(page, {
    profile: "retrieval_only",
    source: "retrieval_suite",
    expectedAllowed: "Knowledge Retrieval Suite",
    forbiddenAllowed: ["Task Planner", "calc_eval"],
  });

  const taskResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(taskResponse.ok()).toBeTruthy();
  const taskPayload = (await taskResponse.json()) as { session_id: string };
  expect(taskPayload.session_id.trim()).not.toBe("");

  const detailPage = await openTaskDetailFromTaskCenter(page, taskId);
  const detailAllowedToolsMeta = detailPage
    .getByTestId("task-detail-trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(detailAllowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(detailAllowedToolsMeta).toContainText("Source retrieval_suite");
  await expect(detailAllowedToolsMeta).toContainText("Knowledge Retrieval Suite");
  await expect(detailAllowedToolsMeta).not.toContainText("Task Planner");
  await expect(detailAllowedToolsMeta).not.toContainText("calc_eval");

  const governanceSummary = detailPage.getByTestId(
    "task-detail-governance-summary",
  );
  await expect(governanceSummary).toBeVisible({ timeout: 20_000 });
  await expect(governanceSummary).toContainText("retrieval_only");
  await expect(governanceSummary).toContainText("retrieval_suite");
  await expect(governanceSummary).toContainText("Knowledge Retrieval Suite");

  const taskExportJsonResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/export/json`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(taskExportJsonResponse.ok()).toBeTruthy();
  const taskExportJsonPayload = (await taskExportJsonResponse.json()) as {
    trace?: {
      governance?: {
        profile?: string;
        provider_source?: string;
        allowed_tool_labels?: string[];
      };
    };
  };
  expect(taskExportJsonPayload.trace?.governance?.profile).toBe("retrieval_only");
  expect(taskExportJsonPayload.trace?.governance?.provider_source).toBe(
    "retrieval_suite",
  );
  expect(taskExportJsonPayload.trace?.governance?.allowed_tool_labels).toEqual([
    "Knowledge Retrieval Suite",
  ]);

  const sessionExportJsonResponse = await request.get(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(taskPayload.session_id)}/export/json`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(sessionExportJsonResponse.ok()).toBeTruthy();
  const sessionExportJsonPayload = (await sessionExportJsonResponse.json()) as {
    governance?: {
      profiles?: string[];
      provider_sources?: string[];
      allowed_tool_labels?: string[];
    };
  };
  expect(sessionExportJsonPayload.governance?.profiles).toContain("retrieval_only");
  expect(sessionExportJsonPayload.governance?.provider_sources).toContain(
    "retrieval_suite",
  );
  expect(sessionExportJsonPayload.governance?.allowed_tool_labels).toContain(
    "Knowledge Retrieval Suite",
  );

  await detailPage.close();
});

test("saved calculator suite source propagates through runtime and export governance", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  const savedPayload = await saveToolRegistryProfile(page, "calculator_only", {
    source: "calculator_suite",
  });
  expect(savedPayload.tool_registry_profile).toBe("calculator_only");
  expect(savedPayload.tool_registry_provider_source).toBe("calculator_suite");
  expect(savedPayload.enabled_tool_labels).toEqual(["Calculator Suite"]);

  const taskId = await submitPromptAndCaptureTaskId(
    page,
    "Please execute calculator suite runtime acceptance [calc:18/3+4]",
  );

  const allowedToolsMeta = page
    .getByTestId("trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(allowedToolsMeta).toContainText("Profile calculator_only");
  await expect(allowedToolsMeta).toContainText("Source calculator_suite");
  await expect(allowedToolsMeta).toContainText("Calculator Suite");
  await expect(allowedToolsMeta).not.toContainText("Task Planner");
  await expect(allowedToolsMeta).not.toContainText("Knowledge Retrieval");

  await assertInspectorSessionGovernance(page, {
    profile: "calculator_only",
    source: "calculator_suite",
    expectedAllowed: "Calculator Suite",
    forbiddenAllowed: ["Task Planner", "Knowledge Retrieval"],
  });

  const taskResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(taskResponse.ok()).toBeTruthy();
  const taskPayload = (await taskResponse.json()) as { session_id: string };
  expect(taskPayload.session_id.trim()).not.toBe("");

  const detailPage = await openTaskDetailFromTaskCenter(page, taskId);
  const detailAllowedToolsMeta = detailPage
    .getByTestId("task-detail-trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(detailAllowedToolsMeta).toBeVisible({ timeout: 20_000 });
  await expect(detailAllowedToolsMeta).toContainText("Source calculator_suite");
  await expect(detailAllowedToolsMeta).toContainText("Calculator Suite");
  await expect(detailAllowedToolsMeta).not.toContainText("Task Planner");
  await expect(detailAllowedToolsMeta).not.toContainText("Knowledge Retrieval");

  const governanceSummary = detailPage.getByTestId(
    "task-detail-governance-summary",
  );
  await expect(governanceSummary).toBeVisible({ timeout: 20_000 });
  await expect(governanceSummary).toContainText("calculator_only");
  await expect(governanceSummary).toContainText("calculator_suite");
  await expect(governanceSummary).toContainText("Calculator Suite");

  const taskExportJsonResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/export/json`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(taskExportJsonResponse.ok()).toBeTruthy();
  const taskExportJsonPayload = (await taskExportJsonResponse.json()) as {
    trace?: {
      governance?: {
        profile?: string;
        provider_source?: string;
        allowed_tool_labels?: string[];
      };
    };
  };
  expect(taskExportJsonPayload.trace?.governance?.profile).toBe("calculator_only");
  expect(taskExportJsonPayload.trace?.governance?.provider_source).toBe(
    "calculator_suite",
  );
  expect(taskExportJsonPayload.trace?.governance?.allowed_tool_labels).toEqual([
    "Calculator Suite",
  ]);

  const sessionExportJsonResponse = await request.get(
    `${API_BASE_URL}/api/sessions/${encodeURIComponent(taskPayload.session_id)}/export/json`,
    {
      headers: {
        Authorization: `Bearer ${auth.access_token}`,
      },
    },
  );
  expect(sessionExportJsonResponse.ok()).toBeTruthy();
  const sessionExportJsonPayload = (await sessionExportJsonResponse.json()) as {
    governance?: {
      profiles?: string[];
      provider_sources?: string[];
      allowed_tool_labels?: string[];
    };
  };
  expect(sessionExportJsonPayload.governance?.profiles).toContain("calculator_only");
  expect(sessionExportJsonPayload.governance?.provider_sources).toContain(
    "calculator_suite",
  );
  expect(sessionExportJsonPayload.governance?.allowed_tool_labels).toContain(
    "Calculator Suite",
  );

  await detailPage.close();
});

for (const acceptanceCase of [
  {
    profile: "planning_only" as const,
    prompt: "Need rag context and [calc:2+3] but keep runtime restricted to planning only",
    expectedAllowed: "Task Planner",
    forbiddenAllowed: ["Knowledge Retrieval", "calc_eval"],
    expectedTraceCard: "Task Planner",
  },
  {
    profile: "retrieval_only" as const,
    prompt: "Retrieve kb context for the active runtime profile [kb:detail-check]",
    expectedAllowed: "Knowledge Retrieval",
    forbiddenAllowed: ["Task Planner", "calc_eval"],
    expectedTraceCard: "Knowledge Retrieval",
  },
  {
    profile: "calculator_only" as const,
    prompt: "Please calculate this for the task detail replay [calc:40/5+6]",
    expectedAllowed: "calc_eval",
    forbiddenAllowed: ["Task Planner", "Knowledge Retrieval"],
    expectedTraceCard: "calc_eval",
  },
]) {
  test(`task detail replay preserves ${acceptanceCase.profile} registry trace metadata`, async ({
    page,
    request,
  }) => {
    const auth = await registerViaApi(request);
    await seedBrowserAuth(page, auth);

    await page.goto("/");
    await ensureWorkbenchReady(page, auth);
    const savedPayload = await saveToolRegistryProfile(page, acceptanceCase.profile);
    expect(savedPayload.tool_registry_profile).toBe(acceptanceCase.profile);

    const taskId = await submitPromptAndCaptureTaskId(
      page,
      acceptanceCase.prompt,
    );

    await expect(
      page.locator("article.message-row.assistant").filter({
        hasText: "This is a mock response from InsightAgent",
      }).first(),
    ).toBeVisible({ timeout: 20_000 });

    const detailPage = await openTaskDetailFromTaskCenter(page, taskId);
    const allowedToolsMeta = detailPage
      .getByTestId("task-detail-trace-card-meta")
      .filter({ hasText: "Allowed tools" })
      .first();
    await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
    await expect(allowedToolsMeta).toContainText(
      `Profile ${acceptanceCase.profile}`,
    );
    await expect(allowedToolsMeta).toContainText("Source default");
    await expect(allowedToolsMeta).toContainText(acceptanceCase.expectedAllowed);
    for (const forbidden of acceptanceCase.forbiddenAllowed) {
      await expect(allowedToolsMeta).not.toContainText(forbidden);
    }

    const governanceSummary = detailPage.getByTestId(
      "task-detail-governance-summary",
    );
    await expect(governanceSummary).toBeVisible({ timeout: 20_000 });
    await expect(governanceSummary).toContainText(acceptanceCase.profile);
    await expect(governanceSummary).toContainText("default");
    await expect(governanceSummary).toContainText(
      acceptanceCase.expectedAllowed,
    );
    for (const forbidden of acceptanceCase.forbiddenAllowed) {
      await expect(governanceSummary).not.toContainText(forbidden);
    }

    await expect(
      detailPage
        .getByTestId("task-detail-trace-card")
        .filter({ hasText: acceptanceCase.expectedTraceCard })
        .first(),
    ).toBeVisible({ timeout: 20_000 });

    const detailTraceText = await detailPage
      .getByTestId("task-detail-trace-feed")
      .textContent();
    expect(detailTraceText ?? "").toContain(acceptanceCase.expectedTraceCard);
    for (const forbidden of acceptanceCase.forbiddenAllowed) {
      expect(detailTraceText ?? "").not.toContain(forbidden);
    }

    const taskDetailUrl = new URL(detailPage.url());
    const detailTaskId = taskDetailUrl.pathname.split("/").filter(Boolean).at(-1) ?? "";
    expect(detailTaskId).not.toBe("");
    expect(detailTaskId).toBe(taskId);

    const exportJsonPayload = (await getJsonWithRetry(
      request,
      `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/export/json`,
      {
        Authorization: `Bearer ${auth.access_token}`,
      },
    )) as {
      trace?: {
        governance?: {
          profile?: string;
          provider_source?: string;
          allowed_tool_labels?: string[];
        };
      };
    };
    expect(exportJsonPayload.trace?.governance?.profile).toBe(
      acceptanceCase.profile,
    );
    expect(exportJsonPayload.trace?.governance?.provider_source).toBe("default");
    expect(exportJsonPayload.trace?.governance?.allowed_tool_labels).toEqual([
      acceptanceCase.expectedAllowed,
    ]);

    const exportMarkdownResponse = await request.get(
      `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}/export/markdown`,
      {
        headers: {
          Authorization: `Bearer ${auth.access_token}`,
        },
      },
    );
    expect(exportMarkdownResponse.ok()).toBeTruthy();
    const exportMarkdown = await exportMarkdownResponse.text();
    expect(exportMarkdown).toContain(
      `- Tool Registry Profile: ${acceptanceCase.profile}`,
    );
    expect(exportMarkdown).toContain("- Tool Registry Source: default");
    expect(exportMarkdown).toContain(
      `- Allowed Tools: ${acceptanceCase.expectedAllowed}`,
    );

    await detailPage.close();
  });
}

test("knowledge governance action buttons keep text style without borders", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const kbId = `kb-governance-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
  await ingestKnowledgeSnippet(request, auth.access_token, {
    knowledgeBaseId: kbId,
    snippet: `governance sample ${Date.now()}`,
    source: "playwright-governance",
  });
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-knowledge-base").click();

  await expect(page.locator(".knowledge-base-governance-ant-modal")).toBeVisible();
  const clearButton = page.getByTestId("kb-governance-action-clear").first();
  const deleteButton = page.getByTestId("kb-governance-action-delete").first();
  await expect(clearButton).toBeVisible();
  await expect(deleteButton).toBeVisible();

  const clearBorderTop = await clearButton.evaluate(
    (el) => getComputedStyle(el).borderTopWidth,
  );
  const deleteBorderTop = await deleteButton.evaluate(
    (el) => getComputedStyle(el).borderTopWidth,
  );
  expect(clearBorderTop).toBe("0px");
  expect(deleteBorderTop).toBe("0px");
});

test("non-admin sees shared kb actions disabled in governance modal", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);

  const sharedKbId = `shared-pw-${Date.now()}`;
  await page.route("**/api/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "pw-non-admin-user",
        email: auth.email,
        display_name: "Playwright Non Admin",
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
            collection: "kb_shared_mock",
            document_count: 3,
          },
        ],
        knowledge_base_count: 1,
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
  const clearButton = sharedRow.getByTestId("kb-governance-action-clear");
  const deleteButton = sharedRow.getByTestId("kb-governance-action-delete");
  await expect(clearButton).toBeDisabled();
  await expect(deleteButton).toBeDisabled();
});

test("settings popover and modal state reset on reopen", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await runTaskToDone(request, auth.access_token, "playwright settings reopen state reset");
  await waitUsageReady(request, auth.access_token);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  await openSettingsMenu(page);
  const themeTrigger = page.getByTestId("settings-section-trigger-theme");
  await themeTrigger.click();
  await expect(themeTrigger).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("sidebar-settings-menu-popover")).toHaveCount(0);

  await openSettingsMenu(page);
  await expect(themeTrigger).toHaveAttribute("aria-expanded", "false");

  const usageEntry = page.getByTestId("settings-menu-usage");
  await usageEntry.click();
  await expect(page.locator(".usage-dashboard-ant-modal")).toBeVisible();

  const providerResponse = page.waitForResponse((response) => {
    if (!response.url().includes("/api/tasks/usage/dashboard")) {
      return false;
    }
    const url = new URL(response.url());
    return url.searchParams.get("source_kind") === "provider";
  });
  await page.getByTestId("usage-source-filter-provider").click();
  await providerResponse;
  await page.keyboard.press("Escape");
  await expect(page.locator(".usage-dashboard-ant-modal")).toBeHidden();

  await openSettingsMenu(page);
  await page.getByTestId("settings-menu-usage").click();
  const selectedSource = page.locator(
    ".usage-source-filter-row .ant-segmented-item-selected [data-testid]",
  );
  await expect(selectedSource).toHaveAttribute("data-testid", "usage-source-filter-all");
  await page.keyboard.press("Escape");

  await openSettingsMenu(page);
  await page.getByTestId("settings-menu-audit").click();
  await expect(page.locator(".audit-modal")).toBeVisible();
  const auditKeyword = page.getByTestId("audit-keyword-filter");
  await auditKeyword.fill("playwright audit reset probe");
  await expect(auditKeyword).toHaveValue("playwright audit reset probe");
  await page.keyboard.press("Escape");
  await expect(page.locator(".audit-modal")).toBeHidden();

  await openSettingsMenu(page);
  await page.getByTestId("settings-menu-audit").click();
  await expect(page.locator(".audit-modal")).toBeVisible();
  await expect(page.getByTestId("audit-keyword-filter")).toHaveValue("");
});
