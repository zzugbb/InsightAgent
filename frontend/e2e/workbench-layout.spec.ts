import { expect, test } from "@playwright/test";

import {
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";
import {
  INSPECTOR_COLLAPSED_STORAGE_KEY,
  INSPECTOR_WIDTH_STORAGE_KEY,
  SIDEBAR_COLLAPSED_STORAGE_KEY,
  SIDEBAR_WIDTH_STORAGE_KEY,
} from "../lib/storage-keys";

test("saved workbench widths survive hydration and reload", async ({ page, request }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await page.evaluate((keys) => {
    localStorage.setItem(keys.sidebarWidth, "360");
    localStorage.setItem(keys.sidebarCollapsed, "0");
    localStorage.setItem(keys.inspectorWidth, "420");
    localStorage.setItem(keys.inspectorCollapsed, "0");
  }, {
    sidebarWidth: SIDEBAR_WIDTH_STORAGE_KEY,
    sidebarCollapsed: SIDEBAR_COLLAPSED_STORAGE_KEY,
    inspectorWidth: INSPECTOR_WIDTH_STORAGE_KEY,
    inspectorCollapsed: INSPECTOR_COLLAPSED_STORAGE_KEY,
  });

  await page.reload();
  await ensureWorkbenchReady(page, auth);
  const shell = page.locator(".app-shell");
  await expect.poll(() => shell.evaluate((element) =>
    getComputedStyle(element).getPropertyValue("--sidebar-width").trim(),
  )).toBe("360px");
  await expect.poll(() => shell.evaluate((element) =>
    getComputedStyle(element).getPropertyValue("--inspector-width").trim(),
  )).toBe("420px");
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), SIDEBAR_WIDTH_STORAGE_KEY))
    .toBe("360");
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), INSPECTOR_WIDTH_STORAGE_KEY))
    .toBe("420");
});

test("narrow drawers close when the viewport widens", async ({ page, request }) => {
  await page.setViewportSize({ width: 800, height: 800 });
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const shell = page.locator(".app-shell");
  const triggers = page.locator(".chat-header-actions .mobile-inspector-trigger");
  await expect(triggers).toHaveCount(2);
  await triggers.last().click();
  await expect(shell).toHaveClass(/inspector-drawer-open/);

  await page.setViewportSize({ width: 1200, height: 800 });
  await expect(shell).not.toHaveClass(/inspector-drawer-open/);
  await page.setViewportSize({ width: 800, height: 800 });
  await expect(shell).not.toHaveClass(/inspector-drawer-open/);

  await triggers.first().click();
  await expect(shell).toHaveClass(/session-drawer-open/);
  await page.setViewportSize({ width: 1200, height: 800 });
  await expect(shell).not.toHaveClass(/session-drawer-open/);
});
