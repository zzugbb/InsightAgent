import { expect, test } from "@playwright/test";

import {
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";

test("model settings discard unsaved remote draft when reopened", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const modal = page.locator(".model-settings-ant-modal");
  async function openModelSettings() {
    await page.getByTestId("sidebar-settings-trigger").click();
    await page.getByTestId("settings-menu-model").click();
    await expect(modal).toBeVisible();
  }

  await openModelSettings();
  await expect(page.getByTestId("model-settings-mode")).toContainText("mock");
  await page.getByTestId("model-settings-mode").click();
  await page
    .locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden)")
    .locator(".ant-select-item-option")
    .filter({ hasText: "remote" })
    .click();
  await page.getByTestId("model-settings-provider").fill("unsaved-provider");

  await modal.locator(".ant-modal-close").click();
  await expect(modal).toBeHidden();
  await openModelSettings();
  await expect(page.getByTestId("model-settings-mode")).toContainText("mock");
  await expect(page.getByTestId("model-settings-provider")).toHaveValue("mock");
});
