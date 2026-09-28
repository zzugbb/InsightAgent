import { expect, test } from "@playwright/test";

import {
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";
import {
  LOCALE_STORAGE_KEY,
  PRIMARY_COLOR_STORAGE_KEY,
  THEME_STORAGE_KEY,
} from "../lib/storage-keys";

test("stored appearance and language survive hydration", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  await page.addInitScript(({ themeKey, colorKey, localeKey }) => {
    localStorage.setItem(themeKey, "light");
    localStorage.setItem(colorKey, "#dc2626");
    localStorage.setItem(localeKey, "en");
  }, {
    themeKey: THEME_STORAGE_KEY,
    colorKey: PRIMARY_COLOR_STORAGE_KEY,
    localeKey: LOCALE_STORAGE_KEY,
  });

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.locator("html")).toHaveAttribute("lang", "en-US");
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.style.getPropertyValue("--accent").trim(),
  )).toBe("#dc2626");

  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-section-trigger-theme").click();
  await expect(
    page.getByTestId("settings-section-panel-theme").locator(".settings-menu-option.is-active"),
  ).toContainText(/Light/i);
  await page.getByTestId("settings-section-trigger-language").click();
  await expect(
    page.getByTestId("settings-section-panel-language").locator(".settings-menu-option.is-active"),
  ).toContainText(/English/i);

  await page.getByTestId("settings-section-trigger-theme").click();
  await page.getByTestId("settings-section-panel-theme")
    .locator(".settings-menu-option")
    .filter({ hasText: /Dark/i })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), THEME_STORAGE_KEY))
    .toBe("dark");

  await page.getByTestId("settings-section-trigger-language").click();
  await page.getByTestId("settings-section-panel-language")
    .locator(".settings-menu-option")
    .first()
    .click();
  await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN");
  await expect.poll(() => page.evaluate((key) => localStorage.getItem(key), LOCALE_STORAGE_KEY))
    .toBe("zh");
});
