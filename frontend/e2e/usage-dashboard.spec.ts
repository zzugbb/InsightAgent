import { expect, test, type Locator } from "@playwright/test";

import {
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

  await page.getByTestId("model-settings-tool-registry-profile").click();
  await page.getByTitle("planning_only", { exact: true }).click();

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

test("saved planning-only profile constrains actual trace allowed tools", async ({
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

  await page.getByTestId("model-settings-tool-registry-profile").click();
  await page.getByTitle("planning_only", { exact: true }).click();

  const saveResponsePromise = page.waitForResponse((response) => {
    return (
      response.url().includes("/api/settings")
      && response.request().method() === "PUT"
    );
  });
  await page.getByTestId("model-settings-save").click();
  const saveResponse = await saveResponsePromise;
  expect(saveResponse.ok()).toBeTruthy();
  const savedPayload = (await saveResponse.json()) as {
    tool_registry_profile?: string;
    enabled_tool_labels?: string[];
  };
  expect(savedPayload.tool_registry_profile).toBe("planning_only");
  expect(savedPayload.enabled_tool_labels).toEqual(["Task Planner"]);

  const metaDescriptions = page.locator(".model-settings-meta-descriptions");
  await expect(metaDescriptions).toContainText("planning_only");
  await expect(metaDescriptions).toContainText("Task Planner");

  await page.keyboard.press("Escape");
  await expect(page.locator(".model-settings-ant-modal")).toBeHidden();

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill(
    "Need rag context and [calc:1+2] for planning-only runtime acceptance",
  );
  await composerSend.click();

  const allowedToolsMeta = page
    .getByTestId("trace-card-meta")
    .filter({ hasText: "Allowed tools" })
    .first();
  await expect(allowedToolsMeta).toBeVisible({ timeout: 20_000 });
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
});

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
