import { expect, test, type APIRequestContext } from "@playwright/test";

import {
  API_BASE_URL,
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";

async function setRemoteSettingsWithUnreachableBaseUrl(
  request: APIRequestContext,
  token: string,
): Promise<void> {
  const response = await request.put(`${API_BASE_URL}/api/settings`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      mode: "remote",
      provider: "zhipu",
      model: "glm-5.1",
      base_url: "http://127.0.0.1:9/v1",
      api_key: "playwright-e2e-dummy-key",
    },
  });
  expect(response.ok()).toBeTruthy();
}

test("remote network failure shows mapped stream error code @smoke", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await setRemoteSettingsWithUnreachableBaseUrl(request, auth.access_token);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill("trigger remote network error");
  await composerSend.click();

  const composerHint = page.getByTestId("composer-hint");
  await expect(composerHint).toContainText("remote_provider_network_error", {
    timeout: 20_000,
  });

  await composerInput.fill("after remote error can continue typing");
  await expect(composerSend).toBeEnabled({ timeout: 20_000 });
});
