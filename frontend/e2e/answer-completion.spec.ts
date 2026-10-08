import { expect, test } from "@playwright/test";
import { seedBrowserAuth } from "./helpers/workbench";
import type { TraceStepPayload } from "../lib/types/trace";

const steps: TraceStepPayload[] = [{ id: "answer", seq: 3, type: "observation", content: "Recorded answer.",
  meta: { step_type: "final_answer", agent_stop_reason: "max_rounds", provider_finish_reason: "length" } }];
const task = { id: "task", session_id: "session", prompt: "Recorded task", status: "completed",
  status_normalized: "completed", trace_json: JSON.stringify(steps), usage_json: null,
  created_at: "2026-10-08T00:00:00Z", updated_at: "2026-10-08T00:00:01Z" };

for (const width of [1440, 390]) {
  test(`answer completion notices persist in chat and task detail at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seedBrowserAuth(page, { access_token: "fixture", refresh_token: "fixture", session_id: "auth" });
    const locale = width === 390 ? "zh" : "en";
    const roundText = locale === "zh" ? "轮次上限" : "tool round limit";
    const lengthText = locale === "zh" ? "可能被截断" : "may be truncated";
    await page.addInitScript((locale) => {
      localStorage.setItem("insightagent.locale", locale);
      localStorage.setItem("insightagent.activeWorkbenchSessionId", "session");
    }, locale);
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (entry) => { if (["error", "warning"].includes(entry.type())) errors.push(entry.text()); });
    let executed = false;
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/stream")) {
        executed = true;
        const event = (name: string, body: object) => `event: ${name}\ndata: ${JSON.stringify(body)}\n\n`;
        return route.fulfill({ contentType: "text/event-stream", body:
          event("start", { task_id: "task", session_id: "session" })
          + event("trace", { task_id: "task", step_id: "answer", step: { ...steps[0], seq: 1, content: "", meta: { step_type: "final_answer" } } })
          + event("token", { task_id: "task", step_id: "answer", delta: "Recorded answer." })
          + event("trace", { task_id: "task", step_id: "answer", step: steps[0] })
          + event("done", { task_id: "task", session_id: "session", step_id: "answer", status: "completed", usage: {} }) });
      }
      let payload: object = { items: [], total: 0, limit: 50, offset: 0, has_more: false };
      if (path === "/api/auth/me") payload = { id: "owner", email: "fixture@example.com", role: "user", display_name: "Answer fixture" };
      if (path === "/api/settings") payload = { mode: "mock", provider: "mock", model: "mock-gpt", api_key_configured: false };
      if (path === "/api/sessions") payload = { items: [{ id: "session", title: "Answer fixture", created_at: task.created_at, updated_at: task.updated_at }], total: 1, limit: 10, offset: 0, has_more: false };
      if (path === "/api/tasks" && route.request().method() === "POST") payload = { task_id: "task", session_id: "session", status: "queued" };
      else if (path === "/api/tasks") payload = { items: executed ? [task] : [], total: executed ? 1 : 0, limit: 50, offset: 0, has_more: false };
      if (path === "/api/tasks/task") payload = task;
      if (path.endsWith("/messages")) payload = { messages: executed ? [
        { id: "user", role: "user", content: "Recorded task", task_id: "task", created_at: task.created_at },
        { id: "assistant", role: "assistant", content: "Recorded answer.", task_id: "task", created_at: task.updated_at },
      ] : [] };
      if (path.endsWith("/trace")) payload = { task_id: "task", steps, status: "completed", status_normalized: "completed" };
      if (path.endsWith("/trace/delta")) payload = { task_id: "task", steps, next_cursor: 3, has_more: false };
      await route.fulfill({ json: payload });
    });
    await page.goto("/");
    await expect(page).toHaveTitle(/InsightAgent/);
    await page.getByTestId("composer-input").fill("Recorded task");
    // The Next dev indicator overlaps the compact Chinese send button; exercise normal Enter submission.
    await page.getByTestId("composer-input").press("Enter");
    const notice = page.getByTestId("answer-notices");
    await expect(notice).toContainText(roundText);
    await expect(notice).toContainText(lengthText);
    await expect(page.locator(".message-row.assistant")).toContainText("Recorded answer.");
    await page.reload();
    await expect(page.getByTestId("answer-notices")).toContainText(lengthText);
    await page.goto("/tasks/task");
    await expect(page.getByTestId("task-detail-status-badge")).toContainText(/completed|已完成/i);
    await expect(page.getByTestId("answer-notices")).toContainText(roundText);
    await expect(page.getByTestId("answer-notices")).toContainText(lengthText);
    await page.screenshot({ path: `/tmp/insightagent-answer-completion-detail-${width}.png`, animations: "disabled" });
    await page.getByRole("link", { name: locale === "zh" ? "返回工作台" : "Back to Workbench" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByTestId("answer-notices")).toContainText(lengthText);
    await page.screenshot({ path: `/tmp/insightagent-answer-completion-chat-${width}.png`, animations: "disabled" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await expect(page.locator("body")).not.toContainText("Application error");
    expect(errors).toEqual([]);
  });
}
