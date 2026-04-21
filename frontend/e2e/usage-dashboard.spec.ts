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
