import { expect, test } from "@playwright/test";
import { seedBrowserAuth } from "./helpers/workbench";
import type { TraceStepPayload } from "../lib/types/trace";

const content = `${"Full trace content. ".repeat(30)}END_OF_FULL_CONTENT`;
const steps: TraceStepPayload[] = [
  { id: "plan", seq: 1, type: "thought", content: "Plan" },
  { id: "a", seq: 2, type: "action", content: "Left tool", meta: {
    plan_node_id: "root", depends_on: [], parallel_group_id: "g", agent_round: 1,
    tool: { name: "calc_eval", status: "done", input: { expression: "2+3" } } } },
  { id: "b", seq: 3, type: "action", content: "Right tool", meta: {
    plan_node_id: "other", depends_on: [], parallel_group_id: "g", agent_round: 1,
    tool: { name: "calc_eval", status: "done", input: { expression: "3+4" } } } },
  { id: "c", seq: 4, type: "action", content: "Dependent tool", meta: {
    plan_node_id: "child", depends_on: ["root"], agent_round: 1,
    tool: { name: "calc_eval", status: "done", input: { expression: "5*2" } } } },
  { id: "decision", seq: 5, type: "thought", content: "No more tools", meta: {
    agent_decision: "no_tools", agent_from_step_ids: ["c"], agent_round: 1 } },
  { id: "final", seq: 6, type: "observation", content, meta: { step_type: "final_answer" } },
];

for (const width of [1440, 390]) {
  test(`Trace Flow dependencies, parallel nodes and full details at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await seedBrowserAuth(page, { access_token: "offline-fixture", refresh_token: "offline-fixture", session_id: "auth" });
    await page.addInitScript((width) => {
      localStorage.setItem("insightagent.locale", "en");
      localStorage.setItem("insightagent.inspectorCollapsed", width < 900 ? "1" : "0");
      localStorage.setItem("insightagent.inspectorWidth", "340");
    }, width);
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("console", (entry) => { if (entry.type() === "error") errors.push(entry.text()); });
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      if (path.endsWith("/stream")) {
        const event = (name: string, data: object) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
        const body = event("start", { task_id: "task", session_id: "session" })
          + steps.map((step) => event("trace", { task_id: "task", step_id: step.id, step })).join("")
          + event("done", { task_id: "task", session_id: "session", step_id: "final", status: "completed", usage: {} });
        return route.fulfill({ contentType: "text/event-stream", body });
      }
      let payload: object = { items: [], total: 0, limit: 50, offset: 0, has_more: false };
      if (path === "/api/auth/me") payload = { id: "owner", email: "fixture@example.com", role: "user", display_name: "Trace fixture" };
      if (path === "/api/settings") payload = { mode: "mock", provider: "mock", model: "mock-gpt", api_key_configured: false };
      if (path === "/api/sessions" && route.request().method() === "POST") payload = { id: "session", title: "Trace fixture", created_at: "2026-10-07", updated_at: "2026-10-07" };
      if (path === "/api/tasks" && route.request().method() === "POST") payload = { task_id: "task", session_id: "session", status: "queued" };
      if (path.endsWith("/messages")) payload = { messages: [] };
      if (path.endsWith("/trace")) payload = { task_id: "task", steps };
      if (path.endsWith("/trace/delta")) payload = { task_id: "task", steps: steps.filter((step) => step.seq! > Number(url.searchParams.get("after_seq") ?? 0)), next_cursor: 6, has_more: false };
      if (path === "/api/tasks/task") payload = { id: "task", session_id: "session", status: "completed", status_normalized: "completed" };
      await route.fulfill({ json: payload });
    });
    await page.goto("/");
    await page.getByTestId("composer-input").fill("Trace fixture");
    await page.getByTestId("composer-send").click();
    if (width < 900) await expect(page.locator(".app-shell")).toHaveClass(/inspector-drawer-open/);
    await page.getByTestId("inspector-tab-trace").click();
    const semanticFilter = page.getByTestId("inspector-trace-semantic-filter");
    expect(await semanticFilter.evaluate((element) => {
      const bounds = element.getBoundingClientRect();
      return [...element.querySelectorAll(".ant-segmented-item")].every((item) => {
        const rect = item.getBoundingClientRect();
        return rect.left >= bounds.left && rect.right <= bounds.right;
      });
    })).toBe(true);
    await semanticFilter.getByText("Failure", { exact: true }).click();
    await expect(semanticFilter.getByRole("radio", { name: "Failure", exact: true })).toBeChecked();
    await semanticFilter.getByText("All semantics", { exact: true }).click();
    await page.locator(".trace-view-toolbar").getByText("Flow", { exact: true }).click();
    await expect(page.locator(".trace-flow-legend")).toContainText("recording order");
    await expect(page.locator('[data-id="dependency:a:c"]')).toHaveCount(1);
    const dependencyPath = page.locator('[data-id="dependency:a:c"] .react-flow__edge-path');
    await expect(dependencyPath).toHaveAttribute("d", /^M.+L/);
    await expect(dependencyPath).toHaveCSS("stroke-width", "3px");
    expect(await dependencyPath.evaluate((element) => (element as SVGGraphicsElement).getBBox().height)).toBeGreaterThan(0);
    await expect(page.locator('[data-id="decision:c:decision"]')).toHaveCount(1);
    await expect(page.locator('[data-id="sequence:a:b"]')).toHaveCount(0);
    const left = page.locator('.react-flow__node[data-id="a"]');
    const right = page.locator('.react-flow__node[data-id="b"]');
    await expect(left).toBeVisible();
    await expect(right).toBeVisible();
    expect(Math.abs((await left.boundingBox())!.y - (await right.boundingBox())!.y)).toBeLessThan(2);
    const final = page.locator('.react-flow__node[data-id="final"]');
    await final.getByText("Content", { exact: true }).click();
    await expect(final.locator(".trace-flow-node__body").first()).toContainText("END_OF_FULL_CONTENT");
    await left.getByText("Step metadata", { exact: true }).click();
    await expect(left.locator("pre")).toContainText('"plan_node_id": "root"');
    await page.screenshot({ path: `/tmp/insightagent-trace-flow-${width}.png`, animations: "disabled" });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await expect(page.locator("#inspector-panel-trace")).not.toContainText("Cannot read properties");
    expect(errors).toEqual([]);
  });
}
