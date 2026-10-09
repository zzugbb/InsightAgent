import type { Locator, Page } from "@playwright/test";

/** Follow the same explicit disclosure step as a user before using hidden controls. */
export async function revealControl(control: Locator): Promise<void> {
  const section = control.locator("xpath=ancestor::details[1]");
  if (await section.count() && await section.getAttribute("open") === null) {
    await section.locator("summary").first().click();
  }
}

export async function openDisclosure(page: Page, testId: string): Promise<void> {
  const section = page.getByTestId(testId);
  if (await section.getAttribute("open") === null) {
    await section.locator("summary").click();
  }
}
