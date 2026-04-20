import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API_BASE_URL =
  process.env.PLAYWRIGHT_API_BASE_URL ?? "http://127.0.0.1:8000";

type AuthBootstrapResponse = {
  email: string;
  password: string;
  access_token: string;
  refresh_token: string;
  session_id: string;
};

type TaskCreateResponse = {
  task_id: string;
  session_id: string;
};

async function registerViaApi(
  request: APIRequestContext,
): Promise<AuthBootstrapResponse> {
  const stamp = `${Date.now()}-${Math.floor(Math.random() * 1_000_000)}`;
  const email = `pw-e2e-${stamp}@example.com`;
  const password = "playwright-e2e-123";
  const response = await request.post(`${API_BASE_URL}/api/auth/register`, {
    data: {
      email,
      password,
      display_name: "Playwright E2E",
    },
  });
  expect(response.ok()).toBeTruthy();
  const payload = (await response.json()) as Omit<
    AuthBootstrapResponse,
    "email" | "password"
  >;
  return {
    email,
    password,
    ...payload,
  };
}

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

async function ensureWorkbenchReady(
  page: Page,
  creds: Pick<AuthBootstrapResponse, "email" | "password">,
): Promise<void> {
  const settingsTrigger = page.getByTestId("sidebar-settings-trigger");
  const alreadyReady = await settingsTrigger
    .isVisible({ timeout: 4_000 })
    .catch(() => false);
  if (alreadyReady) {
    return;
  }

  const emailInput = page.locator("#auth-email");
  const passwordInput = page.locator("#auth-password");
  await expect(emailInput).toBeVisible({ timeout: 15_000 });
  await expect(passwordInput).toBeVisible({ timeout: 15_000 });
  await emailInput.fill(creds.email);
  await passwordInput.fill(creds.password);

  const submitButton = page.locator("button.ant-btn-primary.ant-btn-block");
  await expect(submitButton).toBeVisible({ timeout: 10_000 });
  await submitButton.click();
  await expect(settingsTrigger).toBeVisible({ timeout: 20_000 });
}

test("usage dashboard source trend is visible", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await runTaskToDone(request, auth.access_token);
  await waitUsageReady(request, auth.access_token);

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
