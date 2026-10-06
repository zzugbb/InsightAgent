import { expect, test } from "@playwright/test";

import { API_BASE_URL, ensureWorkbenchReady, registerViaApi, runTaskToDone, seedBrowserAuth } from "./helpers/workbench";

test("rerun creates an isolated branch, executes in workbench and links back to unchanged source", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  const parent = await runTaskToDone(request, auth.access_token, "original branch fixture");
  const before = await (await request.get(`${API_BASE_URL}/api/tasks/${parent.task_id}/export/json`, { headers })).json();
  await seedBrowserAuth(page, auth);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
  await page.goto(`/tasks/${parent.task_id}`);
  await expect(page).toHaveTitle("InsightAgent");
  await expect(page.getByTestId("task-detail-page")).toBeVisible();
  await page.getByTestId("task-rerun-open").click();
  await expect(page.getByTestId("task-rerun-input")).toHaveValue("original branch fixture");
  await page.getByTestId("task-rerun-input").fill("edited branch fixture calculate 2 + 3");
  await page.getByTestId("task-rerun-confirm").click();
  await expect(page).toHaveURL(/\/$/);
  await ensureWorkbenchReady(page, auth);
  const children = await (await request.get(`${API_BASE_URL}/api/tasks/${parent.task_id}/reruns`, { headers })).json();
  expect(children.total).toBe(1);
  const child = children.items[0];
  expect(child.session_id).not.toBe(parent.session_id);
  await expect.poll(async () => (await (await request.get(`${API_BASE_URL}/api/tasks/${child.task_id}`, { headers })).json()).status_normalized,
    { timeout: 30_000 }).toBe("completed");
  const output = await (await request.get(`${API_BASE_URL}/api/tasks/${child.task_id}/export/json`, { headers })).json();
  expect(output.task.prompt).toBe("edited branch fixture calculate 2 + 3");
  expect(output.trace.steps.length).toBeGreaterThan(0);
  const after = await (await request.get(`${API_BASE_URL}/api/tasks/${parent.task_id}/export/json`, { headers })).json();
  expect(after.task).toEqual(before.task);
  expect(after.trace).toEqual(before.trace);
  expect(after.messages).toEqual(before.messages);
  await page.goto(`/tasks/${child.task_id}`);
  await expect(page.getByTestId("task-rerun-parent")).toHaveAttribute("href", `/tasks/${parent.task_id}`);
  await page.getByTestId("task-rerun-parent").click();
  await expect(page.getByTestId(`task-rerun-child-${child.task_id}`)).toBeVisible();
  await expect(page.locator("nextjs-portal [data-nextjs-dialog]")).toHaveCount(0);
  await expect(page.locator(".task-detail-shell")).toHaveCSS("opacity", "1");
  await page.screenshot({ path: "/tmp/insightagent-task-rerun-desktop.png" });
  expect(errors).toEqual([]);
});

test("uncertain accepted submission retries the same key and creates only one branch", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  const parent = await runTaskToDone(request, auth.access_token, "idempotent branch fixture");
  await seedBrowserAuth(page, auth);
  const keys: string[] = [];
  await page.route(`**/api/tasks/${parent.task_id}/reruns`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    keys.push(route.request().postDataJSON().idempotency_key);
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    if (keys.length === 1) await route.fulfill({ status: 503, json: { detail: "fixture uncertain delivery" } });
    else await route.fulfill({ response });
  });
  await page.goto(`/tasks/${parent.task_id}`);
  await page.getByTestId("task-rerun-open").click();
  await page.getByTestId("task-rerun-confirm").click();
  await expect(page.getByRole("dialog")).toContainText(/Branch creation failed|分支创建失败/);
  await expect(page.getByTestId("task-rerun-input")).toBeDisabled();
  await page.getByTestId("task-rerun-confirm").click();
  await expect(page).toHaveURL(/\/$/);
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  const response = await request.get(`${API_BASE_URL}/api/tasks/${parent.task_id}/reruns`, {
    headers: { Authorization: `Bearer ${auth.access_token}` },
  });
  expect((await response.json()).total).toBe(1);
});

test("active source disables rerun and lineage failure recovers without a false empty state", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  const created = await (await request.post(`${API_BASE_URL}/api/tasks`, {
    headers: { Authorization: `Bearer ${auth.access_token}` }, data: { user_input: "queued source fixture" },
  })).json();
  await seedBrowserAuth(page, auth);
  let fail = true;
  await page.route(`**/api/tasks/${created.task_id}/reruns?**`, (route) => fail
    ? route.fulfill({ status: 503, json: { detail: "fixture unavailable" } }) : route.continue());
  await page.goto(`/tasks/${created.task_id}`);
  const panel = page.getByTestId("task-rerun-panel");
  await expect(page.getByTestId("task-rerun-open")).toBeDisabled();
  await expect(panel).toContainText(/Task branches failed|分支关系加载失败/, { timeout: 15_000 });
  await expect(panel).not.toContainText(/No rerun branches|暂无重跑分支/);
  fail = false;
  await panel.getByRole("button", { name: /Retry|重试/ }).click();
  await expect(panel).toContainText(/No rerun branches|暂无重跑分支/);
});

test("mobile branch lineage paginates and stays within the viewport", async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const auth = await registerViaApi(request);
  const parent = await runTaskToDone(request, auth.access_token, "mobile branch fixture");
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  for (let i = 0; i < 11; i++) {
    const response = await request.post(`${API_BASE_URL}/api/tasks/${parent.task_id}/reruns`, {
      headers, data: { user_input: `mobile branch ${i}`, idempotency_key: crypto.randomUUID() },
    });
    expect(response.status()).toBe(201);
  }
  await seedBrowserAuth(page, auth);
  await page.goto(`/tasks/${parent.task_id}`);
  const panel = page.getByTestId("task-rerun-panel");
  await expect(panel.locator('[data-testid^="task-rerun-child-"]')).toHaveCount(10);
  await panel.locator(".ant-pagination-item-2").click();
  await expect(panel.locator('[data-testid^="task-rerun-child-"]')).toHaveCount(1);
  await panel.scrollIntoViewIfNeeded();
  const bounds = await panel.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
  await expect(page.locator(".task-detail-shell")).toHaveCSS("opacity", "1");
  await page.screenshot({ path: "/tmp/insightagent-task-rerun-mobile.png" });
});
