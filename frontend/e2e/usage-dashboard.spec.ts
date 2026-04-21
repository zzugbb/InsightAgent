import { expect, test, type APIRequestContext } from "@playwright/test";

import {
  API_BASE_URL,
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";

type TaskCreateResponse = {
  task_id: string;
  session_id: string;
};

async function runTaskToDone(
  request: APIRequestContext,
  token: string,
): Promise<void> {
  const createResponse = await request.post(`${API_BASE_URL}/api/tasks`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      user_input: "playwright usage dashboard visual smoke",
    },
  });
  expect(createResponse.ok()).toBeTruthy();
  const created = (await createResponse.json()) as TaskCreateResponse;
  expect(typeof created.task_id).toBe("string");
  expect(created.task_id.trim().length).toBeGreaterThan(0);

  const streamResponse = await request.get(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(created.task_id)}/stream`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
  expect(streamResponse.ok()).toBeTruthy();
  const streamText = await streamResponse.text();
  expect(streamText).toContain("event: done");
}

async function waitUsageReady(
  request: APIRequestContext,
  token: string,
): Promise<void> {
  await expect
    .poll(
      async () => {
        const response = await request.get(`${API_BASE_URL}/api/tasks/usage/dashboard`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (!response.ok()) {
          return -1;
        }
        const payload = (await response.json()) as {
          summary?: { tasks_with_usage?: number };
        };
        return Number(payload.summary?.tasks_with_usage ?? 0);
      },
      { timeout: 20_000, intervals: [500, 1000, 1500, 2000] },
    )
    .toBeGreaterThan(0);
}

test("usage dashboard source trend is visible @smoke", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await runTaskToDone(request, auth.access_token);
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
  await page.keyboard.press("Escape");
  await expect(page.locator(".knowledge-base-governance-ant-modal")).toBeHidden();

  await settingsTrigger.click();
  const modelEntry = page.getByTestId("settings-menu-model");
  await expect(modelEntry).toBeVisible();
  await modelEntry.click();
  await expect(page.locator(".model-settings-ant-modal")).toBeVisible();
});
