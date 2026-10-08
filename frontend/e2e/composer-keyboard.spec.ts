import { expect, test } from "@playwright/test";

import { seedBrowserAuth } from "./helpers/workbench";

for (const width of [1440, 390]) {
  test(`composer preserves IME confirmation and keyboard sending at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seedBrowserAuth(page, {
      access_token: "offline-fixture", refresh_token: "offline-fixture", session_id: "auth",
    });
    await page.addInitScript(() => {
      localStorage.setItem("insightagent.locale", "zh");
      localStorage.setItem("insightagent.inspectorCollapsed", "1");
    });
    const errors: string[] = [];
    const submitted: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith("/stream")) {
        const event = (name: string, data: object) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
        const step = { id: "final", seq: 1, type: "observation", content: "已收到完整输入", meta: { step_type: "final_answer" } };
        return route.fulfill({ contentType: "text/event-stream", body:
          event("start", { task_id: "task", session_id: "session" })
          + event("trace", { task_id: "task", step_id: step.id, step })
          + event("token", { task_id: "task", delta: step.content })
          + event("done", { task_id: "task", session_id: "session", status: "completed", usage: {} }),
        });
      }
      let payload: object = { items: [], total: 0, limit: 50, offset: 0, has_more: false };
      if (path === "/api/auth/me") payload = { id: "owner", email: "fixture@example.com", role: "user", display_name: "输入测试" };
      if (path === "/api/settings") payload = { mode: "mock", provider: "mock", model: "mock-gpt", api_key_configured: false };
      if (path === "/api/sessions" && route.request().method() === "POST") payload = { id: "session", title: "输入测试", created_at: "2026-10-08", updated_at: "2026-10-08" };
      if (path === "/api/tasks" && route.request().method() === "POST") {
        submitted.push(route.request().postDataJSON().user_input);
        payload = { task_id: "task", session_id: "session", status: "queued" };
      }
      if (path.endsWith("/messages")) payload = { messages: submitted.length ? [
        { id: "user", session_id: "session", task_id: "task", role: "user", content: submitted[0], created_at: "2026-10-08" },
        { id: "assistant", session_id: "session", task_id: "task", role: "assistant", content: "已收到完整输入", created_at: "2026-10-08" },
      ] : [] };
      if (path.endsWith("/trace")) payload = { task_id: "task", steps: [] };
      if (path.endsWith("/trace/delta")) payload = { task_id: "task", steps: [], next_cursor: 0, has_more: false };
      if (path === "/api/tasks/task") payload = { id: "task", session_id: "session", status: "completed", status_normalized: "completed" };
      await route.fulfill({ json: payload });
    });

    await page.goto("/");
    await expect(page).toHaveTitle("InsightAgent");
    const input = page.getByTestId("composer-input");
    const send = page.getByTestId("composer-send");
    await expect(input).toBeVisible();
    await expect(send).toBeDisabled();
    await input.fill("请分析知识库");
    await expect(send).toBeEnabled();

    // Native composition flag, then WebKit's legacy 229 confirmation signal.
    for (const keyboard of [{ isComposing: true, keyCode: 13 }, { isComposing: false, keyCode: 229 }]) {
      const allowed = await input.evaluate((element, keyboard) => element.dispatchEvent(new KeyboardEvent("keydown", {
        key: "Enter", code: "Enter", bubbles: true, cancelable: true, ...keyboard,
      })), keyboard);
      expect(allowed).toBe(true);
      await expect(input).toHaveValue("请分析知识库");
      expect(submitted).toEqual([]);
    }

    // Composition lifecycle also protects browsers that omit the native flag.
    await input.dispatchEvent("compositionstart", { data: "库" });
    await input.dispatchEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, isComposing: false });
    await expect(input).toHaveValue("请分析知识库");
    expect(submitted).toEqual([]);
    await input.dispatchEvent("compositionend", { data: "库" });

    await input.press("Shift+Enter");
    await expect(input).toHaveValue("请分析知识库\n");
    expect(submitted).toEqual([]);
    await page.screenshot({ path: `/tmp/insightagent-composer-keyboard-${width}.png`, animations: "disabled" });
    await input.press("Enter");
    await expect.poll(() => submitted).toEqual(["请分析知识库"]);
    await expect(input).toHaveValue("");
    await expect(page.locator("article.message-row.assistant")).toContainText("已收到完整输入");
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await expect(page.locator("nextjs-portal")).not.toContainText("Runtime Error");
    expect(errors).toEqual([]);
  });
}
