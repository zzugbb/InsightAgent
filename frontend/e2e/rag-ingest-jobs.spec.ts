import { expect, test, type Page } from "@playwright/test";

import type { RagIngestJob } from "../app/components/workbench/rag-ingest-jobs";
import { API_BASE_URL, ensureWorkbenchReady, registerViaApi, seedBrowserAuth } from "./helpers/workbench";

const jobId = "00000000-0000-4000-8000-000000000001";
function job(status: RagIngestJob["status"], overrides: Partial<RagIngestJob> = {}): RagIngestJob {
  return { id: jobId, knowledge_base_id: "default", document_total: 1, status,
    result: null, error_code: null, created_at: "2026-10-06T00:00:00Z",
    started_at: null, finished_at: null, ...overrides };
}

async function openDebug(page: Page) {
  if ((page.viewportSize()?.width ?? 1280) < 1024) {
    await page.locator(".chat-header-actions .mobile-inspector-trigger").first().click();
  }
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-runtime-debug").click();
  await expect(page.getByRole("dialog", { name: /Runtime debug|运行调试/ })).toBeVisible();
}

test("background import polls completion, keeps input and restores history after reload", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
  let jobs: RagIngestJob[] = [];
  await page.route("**/api/rag/ingest-jobs**", async (route) => {
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON();
      expect(payload.documents[0].text).toBe("background fixture");
      expect(payload.idempotency_key).toMatch(/^[a-f0-9-]{36}$/);
      jobs = [job("queued")];
      await route.fulfill({ status: 202, json: jobs[0] });
    } else {
      await route.fulfill({ json: { items: jobs } });
    }
  });
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await expect(page).toHaveTitle("InsightAgent");
  await openDebug(page);
  await page.getByTestId("inspector-rag-ingest-input").fill("background fixture");
  await page.getByTestId("rag-ingest-background-submit").click();
  const card = page.getByTestId(`rag-ingest-job-${jobId}`);
  await expect(card).toContainText(/Queued|排队中/);
  jobs = [job("running")];
  await expect(card).toContainText(/Importing|导入中/);
  await expect(card.locator("button")).toHaveCount(0);
  jobs = [job("completed", { result: { knowledge_base_id: "default", collection: "kb_fixture_default",
    documents_ingested: 1, chunks_added: 2, document_count: 2, chunk_size: 500, chunk_overlap: 80 } })];
  await expect(card).toContainText(/Completed|已完成/);
  await expect(card).toContainText(/2/);
  await expect(page.getByTestId("inspector-rag-ingest-input")).toHaveValue("background fixture");
  await expect(page.locator("nextjs-portal [data-nextjs-dialog]")).toHaveCount(0);
  await page.screenshot({ path: "/tmp/insightagent-ingest-desktop.png" });
  await page.reload();
  await ensureWorkbenchReady(page, auth);
  await openDebug(page);
  await expect(card).toContainText(/Completed|已完成/);
  await page.getByTestId(`rag-ingest-job-review-${jobId}`).click();
  await expect(page.getByRole("dialog", { name: /Runtime debug|运行调试/ })).toBeHidden();
  await expect(page.getByRole("dialog", { name: /Knowledge|知识库/ })).toBeVisible();
  expect(errors).toEqual([]);
});

test("queued import can be cancelled and knowledge-base switching isolates its history", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  let state = job("queued");
  await page.route("**/api/rag/ingest-jobs**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/cancel")) {
      state = job("cancelled");
      await route.fulfill({ json: state });
    } else {
      await route.fulfill({ json: { items: url.searchParams.get("knowledge_base_id") === "other" ? [] : [state] } });
    }
  });
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await openDebug(page);
  await page.getByTestId(`rag-ingest-job-cancel-${jobId}`).click();
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toContainText(/Cancelled|已取消/);
  await page.getByTestId("inspector-rag-kb-input").fill("other");
  await page.getByTestId("inspector-rag-kb-apply").click();
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toBeHidden();
  await expect(page.getByTestId("rag-ingest-jobs")).toContainText(/No background|暂无后台/);
});

test("uncertain submission retry reuses its key and failed import shows review guidance", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  const keys: string[] = [];
  let accepted = false;
  await page.route("**/api/rag/ingest-jobs**", async (route) => {
    if (route.request().method() === "POST") {
      keys.push(route.request().postDataJSON().idempotency_key);
      if (keys.length === 1) {
        await route.fulfill({ status: 503, json: { detail: "temporarily unavailable" } });
      } else {
        accepted = true;
        await route.fulfill({ status: 202, json: job("failed", { error_code: "interrupted" }) });
      }
    } else {
      await route.fulfill({ json: { items: accepted ? [job("failed", { error_code: "interrupted" })] : [] } });
    }
  });
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await openDebug(page);
  await page.getByTestId("inspector-rag-ingest-input").fill("keep this draft");
  await page.getByTestId("rag-ingest-background-submit").click();
  await expect(page.getByTestId("rag-ingest-job-submit-error")).toBeVisible();
  await page.getByTestId("rag-ingest-job-submit-retry").click();
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toContainText(/Review the knowledge base|请先复核知识库/);
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
  await expect(page.getByTestId("inspector-rag-ingest-input")).toHaveValue("keep this draft");
});

test("mobile import history keeps cached state visible when refresh fails", async ({ page, request }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const auth = await registerViaApi(request);
  await seedBrowserAuth(page, auth);
  let fail = false;
  await page.route("**/api/rag/ingest-jobs**", async (route) => {
    await route.fulfill(fail ? { status: 503, json: { detail: "temporarily unavailable" } }
      : { json: { items: [job("failed", { error_code: "chroma_unavailable" })] } });
  });
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await openDebug(page);
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toBeVisible();
  fail = true;
  await page.getByTestId("rag-ingest-jobs-refresh").click();
  await expect(page.getByTestId("rag-ingest-jobs-error")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toBeVisible();
  await page.getByTestId(`rag-ingest-job-${jobId}`).scrollIntoViewIfNeeded();
  const card = await page.getByTestId(`rag-ingest-job-${jobId}`).boundingBox();
  expect(card).not.toBeNull();
  expect(card!.x).toBeGreaterThanOrEqual(0);
  expect(card!.x + card!.width).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "/tmp/insightagent-ingest-mobile.png" });
});

test("real background import completes once and its content can be retrieved", async ({ page, request }) => {
  const auth = await registerViaApi(request);
  const headers = { Authorization: `Bearer ${auth.access_token}` };
  const payload = { idempotency_key: crypto.randomUUID(), knowledge_base_id: "background-e2e",
    documents: [{ text: "The background import fixture describes a blue telescope on a mountain.", source: "background-e2e" }] };
  const submissions = await Promise.all([1, 2].map(() => request.post(
    `${API_BASE_URL}/api/rag/ingest-jobs`, { headers, data: payload },
  )));
  expect(submissions.map((response) => response.status())).toEqual([202, 202]);
  const a = await submissions[0].json() as RagIngestJob;
  const b = await submissions[1].json() as RagIngestJob;
  expect(a.id).toBe(b.id);
  await expect.poll(async () => {
    const response = await request.get(`${API_BASE_URL}/api/rag/ingest-jobs/${a.id}`, { headers });
    expect(response.ok()).toBeTruthy();
    return (await response.json() as RagIngestJob).status;
  }, { timeout: 45_000, intervals: [500, 1000, 2000] }).toBe("completed");
  const result = await request.get(`${API_BASE_URL}/api/rag/ingest-jobs/${a.id}`, { headers });
  expect((await result.json() as RagIngestJob).result?.chunks_added).toBe(1);
  expect(await result.text()).not.toContain("blue telescope");
  const query = await request.post(`${API_BASE_URL}/api/rag/query`, {
    headers, data: { knowledge_base_id: "background-e2e", query: "blue telescope", top_k: 3 },
  });
  expect(query.ok()).toBeTruthy();
  const recall = await query.json();
  expect(recall.hit_count).toBe(1);
  expect(recall.hits[0].content).toContain("blue telescope");
  await seedBrowserAuth(page, auth);
  await page.goto("/");
  await ensureWorkbenchReady(page, auth);
  await openDebug(page);
  await page.getByTestId("inspector-rag-kb-input").fill("background-e2e");
  await page.getByTestId("inspector-rag-kb-apply").click();
  await expect(page.getByTestId(`rag-ingest-job-${a.id}`)).toContainText(/Completed|已完成/);
  await page.getByTestId(`rag-ingest-job-${a.id}`).scrollIntoViewIfNeeded();
  await page.screenshot({ path: "/tmp/insightagent-ingest-real.png" });
});
