import { expect, test, type Page } from "@playwright/test";
import { seedBrowserAuth, ACTIVE_WORKBENCH_SESSION_STORAGE_KEY } from "./helpers/workbench";
import { openDisclosure } from "./helpers/disclosure";

test.use({ actionTimeout: 15_000 });

const longTitle = "Review a knowledge base and its execution evidence. ".repeat(12);
const collection = `kb_owner_${"collection-reference-".repeat(12)}`;

async function fixture(page: Page) {
  await seedBrowserAuth(page, { access_token: "offline-fixture", refresh_token: "offline-fixture", session_id: "auth" });
  await page.addInitScript((key) => {
    localStorage.setItem(key, "session");
    localStorage.setItem("insightagent.locale", "en");
  }, ACTIVE_WORKBENCH_SESSION_STORAGE_KEY);
  const writes: string[] = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() !== "GET" && request.method() !== "OPTIONS") writes.push(path);
    let payload: object = { items: [], total: 0, limit: 50, offset: 0, has_more: false };
    if (path === "/api/auth/me") payload = { id: "owner", email: "fixture@example.com", role: "user" };
    if (path === "/api/sessions") payload = { items: [{ id: "session", title: longTitle, created_at: "2026-10-09", updated_at: "2026-10-09" }], total: 1, has_more: false };
    if (path.endsWith("/messages")) payload = { messages: [] };
    if (path === "/api/settings") payload = {
      mode: "remote", provider: "fixture", model: "fixture-model", base_url: "https://example.invalid/v1",
      base_url_configured: true, api_key_configured: true, database_locator: "fixture",
      tool_registry_profile: "default", tool_registry_provider_source: "default",
      available_tool_registry_profiles: ["default"], available_tool_registry_provider_sources: ["default"],
      enabled_tool_labels: ["Calculator"], enabled_tool_names: ["calc_eval"],
    };
    if (path === "/api/rag/knowledge-bases") payload = {
      chroma_reachable: true, error: null, knowledge_base_count: 1,
      knowledge_bases: [{ knowledge_base_id: "research", collection, document_count: 8, document_versions: [] }],
    };
    if (path === "/api/tasks/usage/dashboard") payload = {
      window_days: 14, by_session: [], top_tasks: [],
      summary: { tasks_total: 1, tasks_with_usage: 1, total_tokens: 100, cost_estimate: 0.01,
        avg_total_tokens: 100, avg_cost_estimate: 0.01, source_tasks_provider: 1, source_tasks_estimated: 0,
        source_tasks_mixed: 0, source_tasks_legacy: 0 },
      trend: Array.from({ length: 14 }, (_, i) => ({ day: `2026-10-${String(i + 1).padStart(2, "0")}`,
        total_tokens: 100, cost_estimate: 0.01, source_tasks_provider: 1, source_tasks_estimated: 0,
        source_tasks_mixed: 0, source_tasks_legacy: 0 })),
    };
    await route.fulfill({ json: payload });
  });
  return writes;
}

async function openSettings(page: Page, section: string) {
  if (await page.getByRole("button", { name: "Session list", exact: true }).isVisible()
    && !await page.locator(".app-shell").evaluate((el) => el.classList.contains("session-drawer-open"))) {
    await page.getByRole("button", { name: "Session list", exact: true }).click();
  }
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId(`settings-menu-${section}`).click();
}

for (const width of [1440, 390]) {
  test(`workbench dialogs remain operable and uncluttered at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
    const writes = await fixture(page);
    await page.goto("/");
    await expect(page).toHaveTitle("InsightAgent");
    await expect(page.getByTestId("composer-input")).toBeVisible();
    const title = page.locator(".chat-main-heading .chat-title-text");
    await expect(title).toHaveAttribute("title", longTitle.trim());
    expect(await title.evaluate((el) => el.getBoundingClientRect().height <= parseFloat(getComputedStyle(el).lineHeight) * 2 + 1)).toBeTruthy();
    if (width > 1000) {
      await expect(page.getByTestId("inspector-trace-empty")).toBeVisible();
      await expect(page.getByTestId("inspector-trace-semantic-filter")).toHaveCount(0);
      await page.getByTestId("inspector-trace-empty").getByRole("button").click();
      await expect(page.getByTestId("task-center-keyword-filter")).toBeVisible();
      await page.getByTestId("task-center-close").click();
    }

    await openSettings(page, "model");
    const model = page.locator(".model-settings-ant-modal");
    await expect(page.getByTestId("model-settings-base-url")).toBeVisible();
    await expect(page.getByTestId("model-settings-tool-registry-profile")).toBeHidden();
    await openDisclosure(page, "model-settings-tools-section");
    await openDisclosure(page, "model-settings-diagnostics-section");
    await model.locator(".ant-modal-body").evaluate((el) => { el.scrollTop = el.scrollHeight; });
    const footer = await page.getByTestId("model-settings-save").boundingBox();
    const close = await model.locator(".ant-modal-close").boundingBox();
    expect(footer!.y + footer!.height).toBeLessThanOrEqual(900);
    expect(close!.y).toBeGreaterThanOrEqual(0);
    await expect(page.getByTestId("model-settings-validate")).toBeVisible();
    await model.locator(".ant-modal-close").click();

    await openSettings(page, "knowledge-base");
    const kb = page.locator(".knowledge-base-governance-ant-modal");
    await expect(kb).toBeVisible();
    if (width > 1000) {
      expect(await kb.locator(".ant-table-content").evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBeTruthy();
    }
    await kb.locator(".ant-table-row-expand-icon").click();
    await expect(kb.locator(".kb-collection-detail .identifier-text")).toHaveAttribute("title", collection);
    await kb.locator(".ant-modal-close").click();

    await openSettings(page, "usage");
    const usage = page.locator(".usage-dashboard-ant-modal");
    await expect(usage.locator(".usage-summary-strip")).toBeVisible();
    await expect(page.getByTestId("usage-source-trend-block")).toBeHidden();
    await openDisclosure(page, "usage-trends-section");
    await expect(page.getByTestId("usage-source-trend-block")).toBeVisible();
    await openDisclosure(page, "usage-details-section");
    await expect(page.getByTestId("usage-dashboard-table-wrap")).toBeVisible();
    await usage.locator(".ant-modal-close").click();

    if (await page.locator(".app-shell").evaluate((el) => el.classList.contains("session-drawer-open"))) {
      await page.getByRole("button", { name: "Close session list", exact: true }).click({ position: { x: width - 8, y: 450 } });
    }

    await page.getByTestId("chat-open-task-center").click();
    await expect(page.getByTestId("task-center-keyword-filter")).toBeVisible();
    await expect(page.getByTestId("task-center-governance-profile-filter")).toBeHidden();
    await openDisclosure(page, "task-center-advanced-section");
    await expect(page.getByTestId("task-center-observability-filter")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
    await expect(page.locator('nextjs-portal [data-nextjs-dialog]')).toHaveCount(0);
    expect(errors).toEqual([]);
    expect(writes).toEqual([]);
  });
}

for (const width of [1920, 390]) {
  for (const theme of ["light", "dark"]) {
    test(`login and registration stay bounded at ${width}px in ${theme}`, async ({ page }) => {
      await page.setViewportSize({ width, height: width < 600 ? 844 : 1080 });
      await page.addInitScript((theme) => {
        localStorage.setItem("insightagent.theme", theme);
        localStorage.setItem("insightagent.locale", theme === "dark" ? "zh" : "en");
      }, theme);
      await page.goto("/");
      await expect(page).toHaveTitle("InsightAgent");
      const email = page.locator("#auth-email");
      await expect(email).toBeVisible();
      expect((await email.boundingBox())!.width).toBeLessThanOrEqual(420);
      if (page.context().browser()?.browserType().name() === "chromium") {
        await page.screenshot({ path: `/tmp/insightagent-layout-login-${width}-${theme}.png` });
      }
      await page.getByRole("tab", { name: theme === "dark" ? "注册" : "Sign Up", exact: true }).click();
      await expect(page.locator("#auth-display-name")).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
      await expect(page.locator('nextjs-portal [data-nextjs-dialog]')).toHaveCount(0);
    });
  }
}

test("model footer keeps keyboard submission and discards closed drafts", async ({ page }) => {
  const writes = await fixture(page);
  await page.goto("/");
  await expect(page.getByTestId("composer-input")).toBeVisible();
  await openSettings(page, "model");
  const provider = page.getByTestId("model-settings-provider");
  await provider.fill("unsaved-draft");
  await page.locator(".model-settings-ant-modal .ant-modal-close").click();
  await openSettings(page, "model");
  await expect(provider).toHaveValue("fixture");
  const saved = page.waitForRequest((request) => new URL(request.url()).pathname === "/api/settings" && request.method() === "PUT");
  await provider.press("Enter");
  await saved;
  expect(writes).toEqual(["/api/settings"]);
});
