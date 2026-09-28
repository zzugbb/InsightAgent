import { expect, test } from "@playwright/test";

import {
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";

test("settings menu resets its accordion and positions the portal on reopen", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const trigger = page.getByTestId("sidebar-settings-trigger");
  const popover = page.getByTestId("sidebar-settings-menu-popover");
  const theme = page.getByTestId("settings-section-trigger-theme");

  await trigger.click();
  await expect(popover).toBeVisible();
  await theme.click();
  await expect(theme).toHaveAttribute("aria-expanded", "true");

  await trigger.click();
  await expect(popover).toBeHidden();
  await trigger.click();
  await expect(popover).toBeVisible();
  await expect(theme).toHaveAttribute("aria-expanded", "false");

  await page.setViewportSize({ width: 1024, height: 700 });
  await expect.poll(async () => {
    const triggerBox = await trigger.boundingBox();
    const popoverBox = await popover.boundingBox();
    if (!triggerBox || !popoverBox) return false;
    return Math.abs(triggerBox.x - popoverBox.x) < 2;
  }).toBe(true);
});
