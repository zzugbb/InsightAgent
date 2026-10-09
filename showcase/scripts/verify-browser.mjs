// Explicit local QA against the exported static site on port 3101.
// Uses the parent repository's existing Playwright dependency; never shipped at runtime.
import {
  chromium,
  firefox,
  webkit,
  expect,
} from "../../frontend/node_modules/@playwright/test/index.mjs";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const scriptDirectory = fileURLToPath(new URL(".", import.meta.url));
const runs = JSON.parse(
  fs.readFileSync(path.join(scriptDirectory, "../data/cases.json"), "utf8"),
);
(async () => {
  const result = [];
  for (const [name, engine] of Object.entries({ chromium, firefox, webkit })) {
    const browser = await engine.launch();
    for (const width of [1440, 390]) {
      const context = await browser.newContext({
        viewport: { width, height: 900 },
        reducedMotion: width === 390 ? "reduce" : "no-preference",
      });
      const page = await context.newPage();
      const errors = [],
        unexpected = [];
      page.on("pageerror", (e) => errors.push(e.message));
      page.on("console", (e) => {
        if (e.type() === "error") errors.push(e.text());
      });
      page.on("request", (r) => {
        if (!r.url().startsWith("http://127.0.0.1:3101/"))
          unexpected.push(r.url());
        if (/\/api\//.test(r.url())) unexpected.push("API_REQUEST");
      });
      const noOverflow = async () =>
        expect(
          await page.evaluate(() => document.documentElement.scrollWidth),
        ).toBeLessThanOrEqual(width);
      await page.goto("http://127.0.0.1:3101/");
      await expect(page.getByRole("heading", { level: 1 })).toContainText(
        "InsightAgent",
      );
      expect(
        await page
          .locator(".product-shot img")
          .evaluate((e) => e.complete && e.naturalWidth === 1600),
      ).toBe(true);
      await noOverflow();
      expect(await page.title()).toBe("InsightAgent · 可视化 AI Agent 工作台");
      expect(page.url()).toBe("http://127.0.0.1:3101/");
      await expect(page.locator("[data-nextjs-dialog]")).toHaveCount(0);
      if (name === "chromium") {
        await page.screenshot({
          path: `/tmp/insightagent-showcase-first-${width}.png`,
          fullPage: false,
          animations: "disabled",
        });
        await page.screenshot({
          path: `/tmp/insightagent-showcase-home-${width}.png`,
          fullPage: true,
          animations: "disabled",
        });
      }
      await page
        .getByRole("link", { name: "体验案例回放", exact: true })
        .click();
      await expect(page.getByRole("heading", { level: 1 })).toContainText(
        "展开一次执行",
      );
      expect(await page.title()).toBe("案例体验 · InsightAgent");
      expect(page.url()).toBe("http://127.0.0.1:3101/demo/");
      await expect(page.locator("[data-nextjs-dialog]")).toHaveCount(0);
      await page.clock.install();
      const progress = page.getByRole("progressbar", { name: "回放进度" });
      const advance = async (count) => {
        for (let i = 0; i < count; i++) {
          await page.clock.runFor(1200);
          await expect(progress).toHaveAttribute(
            "aria-valuenow",
            String(i + 1),
          );
        }
      };
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await page.getByRole("button", { name: "播放回放", exact: true }).click();
      await page.clock.runFor(1200);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.getByRole("button", { name: "暂停回放", exact: true }).click();
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.getByRole("button", { name: "播放回放", exact: true }).click();
      for (let i = 2; i <= runs[0].steps.length; i++) {
        await page.clock.runFor(1200);
        await expect(progress).toHaveAttribute("aria-valuenow", String(i));
      }
      await expect(page.locator(".answer-panel")).toContainText("14");
      await expect(
        page.getByRole("button", { name: "重新播放", exact: true }),
      ).toBeVisible();
      await page.locator(".timeline-step").nth(2).focus();
      await page.keyboard.press("Enter");
      await expect(
        page.getByRole("complementary", { name: "节点详情" }),
      ).toContainText("budget.md");
      await page.getByRole("button", { name: "流程图", exact: true }).click();
      await expect(page.locator(".graph-node")).toHaveCount(
        runs[0].steps.length,
      );
      await page.clock.runFor(200);
      await page.locator(".graph-node").nth(4).click();
      await expect(
        page.getByRole("complementary", { name: "节点详情" }),
      ).toContainText("计算工具");
      await expect(page.locator(".graph-legend")).toContainText("记录顺序");
      await noOverflow();
      if (name === "chromium")
        await page.screenshot({
          path: `/tmp/insightagent-showcase-demo-${width}.png`,
          fullPage: true,
          animations: "disabled",
        });
      await page.getByRole("button", { name: "复位回放", exact: true }).click();
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await expect(page.locator(".answer-panel")).toHaveCount(0);
      await page
        .getByRole("button", { name: "02失败与分支恢复", exact: true })
        .click();
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await expect(page.locator(".provenance")).toContainText(
        "不是供应商真实故障",
      );
      await page.getByRole("button", { name: "播放回放", exact: true }).click();
      await advance(runs[1].steps.length);
      await expect(page.locator(".answer-panel")).toContainText("原任务失败");
      await expect(page.locator(".answer-panel")).toContainText(
        "没有生成最终回答",
      );
      await page
        .getByRole("button", { name: "独立分支 · 真实模型", exact: true })
        .click();
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await expect(page.locator(".answer-panel")).toHaveCount(0);
      await page.getByRole("button", { name: "播放回放", exact: true }).click();
      await advance(runs[2].steps.length);
      await expect(page.locator(".answer-panel")).toContainText("10");
      await expect(page.locator(".provenance")).toContainText("真实模型规划");
      await page.getByRole("button", { name: "重新播放", exact: true }).click();
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await page.clock.runFor(1200);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page
        .getByRole("button", { name: "01知识检索与计算", exact: true })
        .click();
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await noOverflow();
      if (width === 390) {
        await page
          .getByRole("button", { name: "播放回放", exact: true })
          .click();
        await page.clock.runFor(1200);
        expect(
          await page
            .locator(".step-detail")
            .evaluate((e) => getComputedStyle(e).animationName),
        ).toBe("none");
      }
      expect(errors).toEqual([]);
      expect(unexpected).toEqual([]);
      result.push({
        browser: name,
        width,
        status: "passed",
        noOverflow: true,
        errors: errors.length,
        externalOrApiRequests: unexpected.length,
      });
      await context.close();
    }
    await browser.close();
  }
  fs.writeFileSync(
    "/tmp/insightagent-showcase-browser.json",
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify({ passed: result.length, results: result }));
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
