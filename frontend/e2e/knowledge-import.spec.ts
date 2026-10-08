import { expect, test, type Page } from "@playwright/test";
import { seedBrowserAuth } from "./helpers/workbench";
import type { RagIngestJob } from "../app/components/workbench/rag-ingest-jobs";

type Payload = { idempotency_key: string; knowledge_base_id: string; documents: { text: string; source: string; document_id: string }[] };
const jobId = "00000000-0000-4000-8000-000000000002";
async function fixture(page: Page, width = 1440, role = "user") {
  await page.setViewportSize({ width, height: 900 });
  await seedBrowserAuth(page, { access_token: "offline-fixture", refresh_token: "offline-fixture", session_id: "auth" });
  await page.addInitScript(() => { localStorage.setItem("insightagent.locale", "en"); });
  const state = { submissions: [] as Payload[], jobs: [] as RagIngestJob[], failOnce: false, chromaReachable: true };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let payload: object = { items: [], total: 0, limit: 50, offset: 0, has_more: false };
    if (path === "/api/auth/me") payload = { id: "owner", email: "fixture@example.com", role, display_name: "Import fixture" };
    if (path === "/api/settings") payload = { mode: "mock", provider: "mock", model: "mock-gpt", api_key_configured: false };
    if (path === "/api/rag/knowledge-bases") {
      const completed = state.jobs.find((job) => job.status === "completed");
      payload = { chroma_reachable: state.chromaReachable, error: null, chroma_url: "fixture", knowledge_base_count: completed ? 1 : 0,
        knowledge_bases: completed ? [{ knowledge_base_id: completed.knowledge_base_id, collection: "kb_fixture", document_count: 2,
          unique_document_count: 2, document_versions: state.submissions.at(-1)?.documents.map((doc) => ({
            source: doc.source, document_id: doc.document_id, document_version: "v1", content_hash: "hash", chunk_count: 1,
          })) }] : [] };
    }
    if (path === "/api/rag/ingest-jobs") {
      if (route.request().method() === "POST") {
        const submission = route.request().postDataJSON() as Payload;
        state.submissions.push(submission);
        if (state.failOnce) { state.failOnce = false; return route.fulfill({ status: 503, json: { detail: "temporarily unavailable" } }); }
        state.jobs = [{ id: jobId, knowledge_base_id: submission.knowledge_base_id, document_total: submission.documents.length,
          status: "queued", result: null, error_code: null, created_at: "2026-10-07T00:00:00Z", started_at: null, finished_at: null }];
        return route.fulfill({ status: 202, json: state.jobs[0] });
      }
      payload = { items: state.jobs.filter((job) => job.knowledge_base_id === new URL(route.request().url()).searchParams.get("knowledge_base_id")) };
    }
    if (path === "/api/rag/status") payload = { knowledge_base_id: "manuals", collection: "kb_fixture", document_count: 2, chroma_reachable: true };
    if (path === "/api/rag/query") {
      expect(route.request().postDataJSON().knowledge_base_id).toBe("manuals");
      payload = { knowledge_base_id: "manuals", collection: "kb_fixture", query: "blue telescope", hit_count: 1,
        hits: [{ id: "hit", content: "A blue telescope on a mountain.", distance: 0.1, metadata: { source: "guide.md", document_id: "guide.md", document_version: "v1" } }] };
    }
    await route.fulfill({ json: payload });
  });
  await page.goto("/");
  if (width < 1024) await page.locator(".chat-header-actions .mobile-inspector-trigger").first().click();
  await page.getByTestId("sidebar-settings-trigger").click();
  await page.getByTestId("settings-menu-knowledge-base").click();
  await expect(page.getByTestId("kb-governance-import")).toBeEnabled();
  return state;
}
const files = [
  { name: "guide.md", mimeType: "text/markdown", buffer: Buffer.from("# Guide\nA blue telescope on a mountain.") },
  { name: "笔记.txt", mimeType: "text/plain", buffer: Buffer.from("中文资料") },
];

for (const width of [1440, 390]) {
  test(`file import, progress, version review and targeted retrieval at ${width}px`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
    const state = await fixture(page, width);
    await page.getByTestId("kb-governance-import").click();
    await page.getByTestId("knowledge-import-target").fill("manuals");
    await page.getByTestId("knowledge-import-files").setInputFiles(files);
    await expect(page.getByTestId("knowledge-import-preview")).toContainText("2 document(s)");
    await page.locator("summary").filter({ hasText: "guide.md" }).click();
    await expect(page.locator("pre").filter({ hasText: "blue telescope" })).toBeVisible();
    await page.getByTestId("rag-ingest-background-submit").click();
    const card = page.getByTestId(`rag-ingest-job-${jobId}`);
    await expect(card).toContainText("Queued");
    expect(state.submissions[0].documents).toEqual(files.map((file) => ({ text: file.buffer.toString(), source: file.name, document_id: file.name })));
    state.jobs[0] = { ...state.jobs[0], status: "running", progress: { documents_processed: 1, chunks_written: 1, chunk_total: 2 } };
    await expect(page.getByTestId(`rag-ingest-job-progress-${jobId}`)).toContainText("1 / 2");
    state.jobs[0] = { ...state.jobs[0], status: "completed" };
    await expect(card).toContainText("Completed");
    const dialog = page.getByRole("dialog", { name: "Import knowledge", exact: true });
    const box = await dialog.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    await page.screenshot({ animations: "disabled", path: `/tmp/insightagent-knowledge-import-${width}.png` });
    await page.getByTestId(`rag-ingest-job-review-${jobId}`).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByTestId("kb-version-detail-panel")).toContainText("guide.md");
    await expect(page.getByTestId("kb-version-detail-panel")).toContainText("笔记.txt");
    await page.screenshot({ animations: "disabled", path: `/tmp/insightagent-knowledge-governance-${width}.png` });
    await page.getByTestId("kb-governance-action-import").click();
    await expect(page.getByTestId("knowledge-import-target")).toHaveValue("manuals");
    await page.getByRole("button", { name: "Back to knowledge bases", exact: true }).click();
    await page.getByTestId("kb-governance-action-query").click();
    await expect(page.getByTestId("inspector-rag-kb-input")).toHaveValue("manuals");
    await page.getByTestId("inspector-rag-query-input").fill("blue telescope");
    await page.getByTestId("inspector-rag-query-submit").click();
    await expect(page.getByRole("dialog")).toContainText("A blue telescope on a mountain.");
    expect(errors).toEqual([]);
  });
}

test("uncertain submission freezes its draft and retries the identical payload and key", async ({ page }) => {
  const state = await fixture(page);
  state.failOnce = true;
  await page.getByTestId("kb-governance-import").click();
  await page.getByTestId("knowledge-import-target").fill("manuals");
  await page.getByTestId("knowledge-import-files").setInputFiles(files);
  await page.getByTestId("rag-ingest-background-submit").click();
  await expect(page.getByTestId("rag-ingest-job-submit-error")).toBeVisible();
  await expect(page.getByTestId("knowledge-import-target")).toBeDisabled();
  await expect(page.getByTestId("knowledge-import-files")).toBeDisabled();
  await expect(page.getByTestId("rag-ingest-background-submit")).toBeDisabled();
  await page.getByTestId("rag-ingest-job-submit-retry").click();
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toContainText("Queued");
  expect(state.submissions).toHaveLength(2);
  expect(state.submissions[0]).toEqual(state.submissions[1]);
  await expect(page.getByTestId("knowledge-import-target")).toBeEnabled();
});

test("invalid files, target IDs and shared permissions block submission", async ({ page }) => {
  const state = await fixture(page);
  await page.getByTestId("kb-governance-import").click();
  const input = page.getByTestId("knowledge-import-files");
  await input.setInputFiles({ name: "bad.pdf", mimeType: "application/pdf", buffer: Buffer.from("data") });
  await expect(page.getByTestId("knowledge-import-file-error")).toContainText("Only .txt");
  await expect(page.getByTestId("rag-ingest-background-submit")).toBeDisabled();
  await input.setInputFiles({ name: "bad.txt", mimeType: "text/plain", buffer: Buffer.from([0xc3, 0x28]) });
  await expect(page.getByTestId("knowledge-import-file-error")).toContainText("UTF-8");
  await input.setInputFiles(files);
  await page.getByTestId("knowledge-import-target").fill("中文");
  await expect(page.getByTestId("rag-ingest-background-submit")).toBeDisabled();
  await page.getByTestId("knowledge-import-target").fill("shared-guide");
  await expect(page.getByRole("dialog")).toContainText("Shared read-only");
  await expect(page.getByTestId("rag-ingest-background-submit")).toBeDisabled();
  expect(state.submissions).toHaveLength(0);
});

test("a stale file read cannot replace a newer selection", async ({ page }) => {
  await page.addInitScript(() => {
    const read = File.prototype.arrayBuffer;
    File.prototype.arrayBuffer = async function () {
      if (this.name === "slow.txt") await new Promise((resolve) => setTimeout(resolve, 400));
      const buffer = await read.call(this);
      if (this.name === "slow.txt") document.documentElement.dataset.slowImportRead = "done";
      return buffer;
    };
  });
  const state = await fixture(page);
  await page.getByTestId("kb-governance-import").click();
  await page.getByTestId("knowledge-import-files").setInputFiles({ name: "slow.txt", mimeType: "text/plain", buffer: Buffer.from("old") });
  await page.getByTestId("knowledge-import-files").setInputFiles(files);
  await expect(page.locator("html")).toHaveAttribute("data-slow-import-read", "done");
  await expect(page.getByTestId("knowledge-import-preview")).toContainText("guide.md");
  await expect(page.getByTestId("knowledge-import-preview")).not.toContainText("slow.txt");
  await page.getByTestId("rag-ingest-background-submit").click();
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toBeVisible();
  expect(state.submissions[0].documents.map((doc) => doc.source)).toEqual(["guide.md", "笔记.txt"]);
});

test("returning to editing requires acknowledgement and creates a new submission", async ({ page }) => {
  const state = await fixture(page);
  state.failOnce = true;
  await page.getByTestId("kb-governance-import").click();
  await page.getByTestId("knowledge-import-files").setInputFiles(files);
  await page.getByTestId("rag-ingest-background-submit").click();
  await expect(page.getByTestId("rag-ingest-job-submit-error")).toBeVisible();
  await page.getByTestId("knowledge-import-edit").click();
  await expect(page.getByRole("tooltip")).toContainText("does not cancel a background job");
  await page.getByRole("tooltip").getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByTestId("knowledge-import-target")).toBeDisabled();
  await page.getByTestId("knowledge-import-edit").click();
  await page.getByRole("tooltip").getByRole("button", { name: "Return to editing", exact: true }).click();
  await expect(page.getByTestId("knowledge-import-target")).toBeEnabled();
  await page.getByTestId("knowledge-import-target").fill("manuals");
  await page.getByTestId("rag-ingest-background-submit").click();
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toContainText("Queued");
  expect(state.submissions).toHaveLength(2);
  expect(state.submissions[0].idempotency_key).not.toBe(state.submissions[1].idempotency_key);
  expect(state.submissions[1].knowledge_base_id).toBe("manuals");
});

test("admins can import shared knowledge; disconnected storage blocks the entry", async ({ page }) => {
  const state = await fixture(page, 1440, "admin");
  state.chromaReachable = false;
  await page.getByTestId("kb-governance-refresh").click();
  await expect(page.getByTestId("kb-governance-import")).toBeDisabled();
  state.chromaReachable = true;
  await page.getByTestId("kb-governance-refresh").click();
  await page.getByTestId("kb-governance-import").click();
  await page.getByTestId("knowledge-import-target").fill("shared-guide");
  await page.getByTestId("knowledge-import-files").setInputFiles(files);
  await expect(page.getByRole("dialog")).toContainText("Shared admin scope");
  await page.getByTestId("rag-ingest-background-submit").click();
  await expect(page.getByTestId(`rag-ingest-job-${jobId}`)).toContainText("Queued");
  expect(state.submissions[0].knowledge_base_id).toBe("shared-guide");
});
