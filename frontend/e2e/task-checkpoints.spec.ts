import { expect, test } from "@playwright/test";
import { API_BASE_URL, ensureWorkbenchReady, registerViaApi, runTaskToDone, seedBrowserAuth } from "./helpers/workbench";

test("experimental checkpoint resumes calculation in a new branch and preserves source", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  const source = await runTaskToDone(request, auth.access_token, "[calc:2+3]");
  const before = await (await request.get(`${API_BASE_URL}/api/tasks/${source.task_id}/export/json`, { headers })).json();
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
  await seedBrowserAuth(page, auth);
  await page.goto(`/tasks/${source.task_id}`);
  await expect(page).toHaveTitle("InsightAgent");
  await expect(page.getByTestId("task-detail-page")).toBeVisible();
  await page.getByTestId("task-checkpoint-open").click();
  await expect(page.getByRole("dialog")).toContainText(/Experimental|实验功能/);
  await expect(page.getByRole("dialog")).toContainText(/Reuse 1|复用 1/);
  await expect(page.getByTestId("task-checkpoint-select")).toContainText("calc_eval");
  await expect(page.locator(".task-detail-shell")).toHaveCSS("opacity", "1");
  await expect(page.locator(".ant-modal")).toHaveCSS("transform", "none");
  await page.screenshot({ animations: "disabled", path: "/tmp/insightagent-checkpoint-desktop.png" });
  await page.getByTestId("task-checkpoint-confirm").click();
  await expect(page).toHaveURL(/\/$/);
  await ensureWorkbenchReady(page, auth);
  const children = await (await request.get(`${API_BASE_URL}/api/tasks/${source.task_id}/reruns`, { headers })).json();
  expect(children.total).toBe(1);
  const child = children.items[0];
  expect(child.session_id).not.toBe(source.session_id);
  await expect.poll(async () => (await (await request.get(`${API_BASE_URL}/api/tasks/${child.task_id}`, { headers })).json()).status_normalized,
    { timeout: 30_000 }).toBe("completed");
  const trace = await (await request.get(`${API_BASE_URL}/api/tasks/${child.task_id}/trace`, { headers })).json();
  expect(trace.steps.some((step: { meta: { checkpoint_reused?: boolean } }) => step.meta?.checkpoint_reused)).toBe(true);
  expect(trace.steps.at(-1).content).toContain("5");
  const after = await (await request.get(`${API_BASE_URL}/api/tasks/${source.task_id}/export/json`, { headers })).json();
  for (const field of ["task", "trace", "messages"]) expect(after[field]).toEqual(before[field]);
  await page.goto(`/tasks/${child.task_id}`);
  await expect(page.getByTestId("task-rerun-parent")).toHaveAttribute("href", `/tasks/${source.task_id}`);
  await expect(page.locator("nextjs-portal [data-nextjs-dialog]")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("mobile checkpoint uncertain delivery freezes step and retries one branch", async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const auth = await registerViaApi(request);
  const source = await runTaskToDone(request, auth.access_token, "[calc:5+7]");
  await seedBrowserAuth(page, auth);
  const bodies: unknown[] = [];
  await page.route(`**/api/tasks/${source.task_id}/reruns`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    bodies.push(route.request().postDataJSON());
    const response = await route.fetch();
    expect(response.status()).toBe(201);
    if (bodies.length === 1) await route.fulfill({ status: 503, json: { detail: "fixture uncertain delivery" } });
    else await route.fulfill({ response });
  });
  await page.goto(`/tasks/${source.task_id}`);
  await page.getByTestId("task-checkpoint-open").click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText(/Reuse 1|复用 1/);
  await expect(page.locator(".task-detail-shell")).toHaveCSS("opacity", "1");
  await expect(page.locator(".ant-modal")).toHaveCSS("transform", "none");
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({ animations: "disabled", path: "/tmp/insightagent-checkpoint-mobile.png" });
  const bounds = await dialog.boundingBox();
  expect(bounds!.x).toBeGreaterThanOrEqual(0);
  expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(390);
  await page.getByTestId("task-checkpoint-confirm").click();
  await expect(dialog).toContainText(/Branch creation failed|分支创建失败/);
  await expect(page.getByTestId("task-checkpoint-select")).toHaveClass(/ant-select-disabled/);
  await page.getByTestId("task-checkpoint-confirm").click();
  await expect(page).toHaveURL(/\/$/);
  expect(bodies).toHaveLength(2);
  expect(bodies[0]).toEqual(bodies[1]);
  const children = await (await request.get(`${API_BASE_URL}/api/tasks/${source.task_id}/reruns`, {
    headers: { Authorization: `Bearer ${auth.access_token}` },
  })).json();
  expect(children.total).toBe(1);
});
