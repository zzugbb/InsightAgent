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
let activePage;
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
      activePage = page;
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
      await page.clock.install();
      const architectureProgress = page.getByRole("progressbar", {
        name: "架构讲解进度",
      });
      const inspector = page.getByRole("region", { name: "执行节点说明" });
      await expect(
        page.locator(".section-number").filter({ hasText: /^0[1-4] \/ / }),
      ).toHaveText([
        "01 / 核心能力",
        "02 / 系统架构",
        "03 / 任务执行",
        "04 / 工程实践",
      ]);
      await expect(
        page.getByRole("button", { name: "系统分层", exact: true }),
      ).toHaveCount(0);
      await page.locator(".system-explorer").scrollIntoViewIfNeeded();
      await expect(page.locator(".architecture-overview button")).toHaveCount(
        5,
      );
      await expect(page.locator(".architecture-overview")).toContainText(
        "REST / SSE",
      );
      await page
        .getByRole("button", { name: "Chroma Memory / RAG 向量", exact: true })
        .click();
      const systemInspector = page.getByRole("region", {
        name: "系统模块说明",
      });
      await expect(systemInspector).toContainText("后端客户端进程");
      await expect(systemInspector).toContainText("没有自动长期语义回忆链");
      await page.locator(".hero").scrollIntoViewIfNeeded();
      await page.clock.runFor(3000);
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "1");
      await page.locator(".architecture-canvas").scrollIntoViewIfNeeded();
      await expect(page.locator(".architecture-graph-node")).toHaveCount(10);
      await page.clock.runFor(300);
      if (width === 390) {
        await expect(
          page.getByRole("button", { name: "播放架构讲解", exact: true }),
        ).toBeVisible();
        await page.clock.runFor(3000);
        await expect(architectureProgress).toHaveAttribute(
          "aria-valuenow",
          "1",
        );
        await page
          .getByRole("button", { name: "播放架构讲解", exact: true })
          .click();
      } else {
        await expect(
          page.getByRole("button", { name: "暂停架构讲解", exact: true }),
        ).toBeVisible();
      }
      await page.clock.runFor(1900);
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "2");
      await expect(page.locator(".architecture-edge-active")).toHaveCount(1);
      await page.clock.runFor(200);
      if (width === 390) {
        expect(
          await page
            .locator(".architecture-edge-active .react-flow__edge-path")
            .evaluate((e) => getComputedStyle(e).animationName),
        ).toBe("none");
        await expect
          .poll(async () => {
            await page.clock.runFor(100);
            const canvasBox = await page
              .locator(".architecture-canvas")
              .boundingBox();
            const selectedBox = await page
              .getByRole("button", { name: "查看模型规划职责", exact: true })
              .boundingBox();
            return (
              selectedBox.x >= canvasBox.x &&
              selectedBox.x + selectedBox.width <=
                canvasBox.x + canvasBox.width &&
              selectedBox.width > 130
            );
          })
          .toBe(true);
      }
      await page
        .getByRole("button", { name: "暂停架构讲解", exact: true })
        .click();
      await page.clock.runFor(3000);
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "2");
      await page.locator(".architecture-steps button").nth(4).focus();
      await page.keyboard.press("Enter");
      await page.clock.runFor(200);
      await expect(inspector).toContainText("计算工具");
      await page.locator(".architecture-canvas").scrollIntoViewIfNeeded();
      await page.clock.runFor(300);
      await page
        .getByRole("button", { name: "查看计算工具职责", exact: true })
        .click();
      await expect(inspector).toContainText("回答中的数字不能代替计算工具");

      // Leaving the graph pauses playback; returning never overrides a visitor's choice.
      await page
        .getByRole("button", { name: "复位架构讲解", exact: true })
        .click();
      await page.locator(".architecture-canvas").scrollIntoViewIfNeeded();
      await page.clock.runFor(200);
      await page
        .getByRole("button", { name: "播放架构讲解", exact: true })
        .click();
      await page.clock.runFor(1900);
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "2");
      await page.locator(".hero").scrollIntoViewIfNeeded();
      await expect(
        page.getByRole("button", { name: "播放架构讲解", exact: true }),
      ).toHaveCount(1);
      await page.clock.runFor(3000);
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "2");
      await page.locator(".architecture-canvas").scrollIntoViewIfNeeded();
      await page.clock.runFor(3000);
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "2");
      await page
        .getByRole("button", { name: "复位架构讲解", exact: true })
        .click();
      await page
        .getByRole("button", { name: "播放架构讲解", exact: true })
        .click();
      for (let i = 2; i <= 8; i++) {
        await page.clock.runFor(1900);
        await expect(architectureProgress).toHaveAttribute(
          "aria-valuenow",
          String(i),
        );
      }
      await expect(
        page.getByRole("button", { name: "重新播放架构讲解", exact: true }),
      ).toBeVisible();
      await page.clock.runFor(4000);
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "8");
      await page
        .getByRole("button", { name: "重新播放架构讲解", exact: true })
        .click();
      await expect(architectureProgress).toHaveAttribute("aria-valuenow", "1");
      await page
        .getByRole("button", { name: "复位架构讲解", exact: true })
        .click();
      await page.locator(".architecture-steps button").nth(5).click();
      await page.clock.runFor(200);
      await expect(inspector).toContainText("反馈决策");
      await page.getByRole("button", { name: "查看全图", exact: true }).click();
      await page.clock.runFor(200);
      await noOverflow();

      if (name === "chromium") {
        await page.locator(".execution").screenshot({
          path: `/tmp/insightagent-showcase-architecture-${width}.png`,
          animations: "disabled",
        });
        await page
          .locator(".architecture")
          .first()
          .screenshot({
            path: `/tmp/insightagent-showcase-system-${width}.png`,
            animations: "disabled",
          });
      }
      // A fresh visit gets one finite autoplay; it does not loop at the end.
      {
        await page.emulateMedia({ reducedMotion: "no-preference" });
        await page.reload();
        await page.locator(".architecture-canvas").scrollIntoViewIfNeeded();
        await expect(
          page.getByRole("button", { name: "暂停架构讲解", exact: true }),
        ).toBeVisible();
        for (let i = 2; i <= 8; i++) {
          await page.clock.runFor(1900);
          await expect(architectureProgress).toHaveAttribute(
            "aria-valuenow",
            String(i),
          );
        }
        await page.clock.runFor(4000);
        await expect(architectureProgress).toHaveAttribute(
          "aria-valuenow",
          "8",
        );
        await expect(
          page.getByRole("button", { name: "重新播放架构讲解", exact: true }),
        ).toBeVisible();
        // Toggling reduced motion stops an active animation and never resumes it.
        await page
          .getByRole("button", { name: "重新播放架构讲解", exact: true })
          .click();
        await page.clock.runFor(1900);
        await expect(architectureProgress).toHaveAttribute(
          "aria-valuenow",
          "2",
        );
        await page.emulateMedia({ reducedMotion: "reduce" });
        await expect(
          page.getByRole("button", { name: "播放架构讲解", exact: true }),
        ).toHaveCount(1);
        await page.emulateMedia({
          reducedMotion: width === 390 ? "reduce" : "no-preference",
        });
        await page.clock.runFor(3000);
        await expect(architectureProgress).toHaveAttribute(
          "aria-valuenow",
          "2",
        );
        // Scrolling over the canvas should continue reading the page, not trap the wheel.
        await page.locator(".architecture-canvas").scrollIntoViewIfNeeded();
        const canvas = await page.locator(".architecture-canvas").boundingBox();
        await page.mouse.move(
          canvas.x + canvas.width / 2,
          canvas.y + canvas.height / 2,
        );
        const beforeScroll = await page.evaluate(() => window.scrollY);
        await page.mouse.wheel(0, -400);
        await expect
          .poll(() => page.evaluate(() => window.scrollY))
          .toBeLessThan(beforeScroll);
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
      await expect(page.locator(".case-observation")).toContainText("14 万元");
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
      const startCase = async () => {
        if (width === 390) {
          await page.clock.runFor(3000);
          await expect(progress).toHaveAttribute("aria-valuenow", "0");
          await expect(page.locator(".replay-manual-hint")).toBeVisible();
          await page
            .getByRole("button", { name: "播放回放", exact: true })
            .click();
        } else {
          await expect(
            page.getByRole("button", { name: "暂停回放", exact: true }),
          ).toBeVisible();
        }
      };
      await page.clock.runFor(200);
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await startCase();
      await page.clock.runFor(1200);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      // Inspecting a node pauses playback; clicking the active case does not restart it.
      await page.locator(".timeline-step").first().focus();
      await page.keyboard.press("Enter");
      await expect(
        page.getByRole("button", { name: "播放回放", exact: true }),
      ).toHaveCount(1);
      await page
        .getByRole("button", { name: "01知识检索与计算", exact: true })
        .click();
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.getByRole("button", { name: "播放回放", exact: true }).click();
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
      await page.getByRole("button", { name: "查看全图", exact: true }).click();
      await page.clock.runFor(200);
      const viewport = page.locator(".graph-canvas .react-flow__viewport");
      const fullTransform = await viewport.getAttribute("style");
      const fullZoom = await viewport.evaluate(
        (e) => new DOMMatrix(getComputedStyle(e).transform).a,
      );
      expect(fullZoom).toBeLessThan(0.5);
      await page.locator(".graph-node").last().focus();
      await page.keyboard.press("Enter");
      await expect(viewport).toHaveAttribute("style", fullTransform);
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
      await expect(page.locator(".case-observation")).toContainText(
        "原失败记录",
      );
      await startCase();
      await advance(runs[1].steps.length);
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute(
        "aria-valuenow",
        String(runs[1].steps.length),
      );
      await expect(
        page.getByRole("button", { name: "原任务 · 受控失败", exact: true }),
      ).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator(".answer-panel")).toContainText("原任务失败");
      await expect(page.locator(".answer-panel")).toContainText(
        "没有生成最终回答",
      );
      await page
        .getByRole("button", { name: "独立分支 · 真实模型", exact: true })
        .click();
      await expect(progress).toHaveAttribute("aria-valuenow", "0");
      await expect(page.locator(".answer-panel")).toHaveCount(0);
      await expect(page.locator(".case-observation")).toContainText(
        "不是从失败步骤接着运行",
      );
      await startCase();
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
      await startCase();
      await page.clock.runFor(1200);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      // Simulate the browser's visibility event to check background pause and no auto-resume.
      await page.evaluate(() => {
        Object.defineProperty(document, "hidden", {
          configurable: true,
          get: () => true,
        });
        document.dispatchEvent(new Event("visibilitychange"));
      });
      await expect(
        page.getByRole("button", { name: "播放回放", exact: true }),
      ).toHaveCount(1);
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.evaluate(() => {
        delete document.hidden;
        document.dispatchEvent(new Event("visibilitychange"));
      });
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.getByRole("button", { name: "复位回放", exact: true }).click();
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
      // A fresh visit in either viewport autoplays once, and changing motion preferences stops it.
      await page.emulateMedia({ reducedMotion: "no-preference" });
      await page.reload();
      await page.clock.runFor(200);
      await expect(
        page.getByRole("button", { name: "暂停回放", exact: true }),
      ).toBeVisible();
      await page.clock.runFor(1200);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.emulateMedia({ reducedMotion: "reduce" });
      await expect(
        page.getByRole("button", { name: "播放回放", exact: true }),
      ).toHaveCount(1);
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.emulateMedia({ reducedMotion: "no-preference" });
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "1");
      await page.getByRole("button", { name: "流程图", exact: true }).click();
      await expect(page.locator(".graph-node")).toHaveCount(1);
      await page.getByRole("button", { name: "播放回放", exact: true }).click();
      await page.clock.runFor(1200);
      await expect(progress).toHaveAttribute("aria-valuenow", "2");
      await page.locator(".graph-node").first().focus();
      await page.keyboard.press("Enter");
      await expect(
        page.getByRole("button", { name: "播放回放", exact: true }),
      ).toHaveCount(1);
      await page.clock.runFor(3000);
      await expect(progress).toHaveAttribute("aria-valuenow", "2");
      await noOverflow();
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
})().catch(async (e) => {
  if (activePage && !activePage.isClosed()) {
    await activePage.screenshot({
      path: "/tmp/insightagent-showcase-failure.png",
      fullPage: false,
    });
  }
  console.error(e);
  process.exit(1);
});
