import { createServer, type Server } from "node:http";

import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

import {
  API_BASE_URL,
  ensureWorkbenchReady,
  registerViaApi,
  seedBrowserAuth,
} from "./helpers/workbench";

async function openInspectorContextTab(page: Page): Promise<void> {
  const contextTab = page
    .locator(".ant-tabs-tab")
    .filter({ has: page.getByTestId("inspector-tab-context") });
  await expect(contextTab).toBeVisible();
  await contextTab.click();
  await expect(page.locator("#inspector-panel-context")).toBeVisible();
}

async function setRemoteSettingsWithUnreachableBaseUrl(
  request: APIRequestContext,
  token: string,
): Promise<void> {
  const response = await request.put(`${API_BASE_URL}/api/settings`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      mode: "remote",
      provider: "zhipu",
      model: "glm-5.1",
      base_url: "http://127.0.0.1:9/v1",
      api_key: "playwright-e2e-dummy-key",
    },
  });
  expect(response.ok()).toBeTruthy();
}

async function setRemoteSettings(
  request: APIRequestContext,
  token: string,
  baseUrl: string,
): Promise<void> {
  const response = await request.put(`${API_BASE_URL}/api/settings`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data: {
      mode: "remote",
      provider: "zhipu",
      model: "glm-5.1",
      base_url: baseUrl,
      api_key: "playwright-e2e-dummy-key",
    },
  });
  expect(response.ok()).toBeTruthy();
}

async function startMockRemoteProvider(args: {
  statusCode: number;
  body: Record<string, unknown>;
}): Promise<{
  baseUrl: string;
  close: () => Promise<void>;
}> {
  let server: Server | null = null;
  const booted = await new Promise<Server>((resolve, reject) => {
    const next = createServer((req, res) => {
      if (req.method !== "POST" || req.url !== "/v1/chat/completions") {
        res.statusCode = 404;
        res.setHeader("content-type", "application/json; charset=utf-8");
        res.end(JSON.stringify({ error: { message: "not found" } }));
        return;
      }
      res.statusCode = args.statusCode;
      res.setHeader("content-type", "application/json; charset=utf-8");
      res.end(JSON.stringify(args.body));
    });
    next.once("error", reject);
    next.listen(0, "127.0.0.1", () => resolve(next));
  });

  server = booted;
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("mock provider server did not expose a tcp address");
  }

  const close = async () =>
    new Promise<void>((resolve, reject) => {
      if (!server) {
        resolve();
        return;
      }
      server.close((err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve();
      });
      server = null;
    });

  return {
    baseUrl: `http://127.0.0.1:${address.port}/v1`,
    close,
  };
}

async function startMockRemoteStreamingProvider(args?: {
  tokenDelayMs?: number;
  tokenCount?: number;
}): Promise<{
  baseUrl: string;
  close: () => Promise<void>;
  getRequestCount: () => number;
}> {
  let server: Server | null = null;
  let requestCount = 0;
  const tokenDelayMs = Math.max(20, args?.tokenDelayMs ?? 140);
  const tokenCount = Math.max(6, args?.tokenCount ?? 22);
  const booted = await new Promise<Server>((resolve, reject) => {
    const next = createServer((req, res) => {
      if (req.method !== "POST" || req.url !== "/v1/chat/completions") {
        res.statusCode = 404;
        res.setHeader("content-type", "application/json; charset=utf-8");
        res.end(JSON.stringify({ error: { message: "not found" } }));
        return;
      }
      requestCount += 1;
      let raw = "";
      req.setEncoding("utf-8");
      req.on("data", (chunk) => {
        raw += chunk;
      });
      req.on("end", () => {
        let stream = false;
        try {
          const parsed = JSON.parse(raw) as { stream?: boolean };
          stream = parsed.stream === true;
        } catch {
          stream = false;
        }
        if (!stream) {
          res.statusCode = 200;
          res.setHeader("content-type", "application/json; charset=utf-8");
          res.end(
            JSON.stringify({
              choices: [
                {
                  message: {
                    content: "playwright remote non-stream response",
                  },
                },
              ],
              usage: {
                prompt_tokens: 11,
                completion_tokens: 12,
                total_tokens: 23,
              },
            }),
          );
          return;
        }

        res.statusCode = 200;
        res.setHeader("content-type", "text/event-stream; charset=utf-8");
        res.setHeader("cache-control", "no-cache");
        res.setHeader("connection", "keep-alive");
        const tokens = Array.from(
          { length: tokenCount },
          (_, idx) => `remote-stream-token-${idx} `,
        );
        let i = 0;
        let timer: ReturnType<typeof setTimeout> | null = null;
        const flushNext = () => {
          if (res.writableEnded || res.destroyed) {
            return;
          }
          if (i >= tokens.length) {
            res.write(
              `data: ${JSON.stringify({
                usage: {
                  prompt_tokens: 21,
                  completion_tokens: tokenCount,
                  total_tokens: 21 + tokenCount,
                },
              })}\n\n`,
            );
            res.write("data: [DONE]\n\n");
            res.end();
            return;
          }
          res.write(
            `data: ${JSON.stringify({
              choices: [{ delta: { content: tokens[i] } }],
            })}\n\n`,
          );
          i += 1;
          timer = setTimeout(flushNext, tokenDelayMs);
        };
        res.once("close", () => {
          if (timer) {
            clearTimeout(timer);
            timer = null;
          }
        });
        flushNext();
      });
    });
    next.once("error", reject);
    next.listen(0, "127.0.0.1", () => resolve(next));
  });

  server = booted;
  const address = server.address();
  if (!address || typeof address === "string") {
    throw new Error("mock provider server did not expose a tcp address");
  }

  const close = async () =>
    new Promise<void>((resolve, reject) => {
      if (!server) {
        resolve();
        return;
      }
      server.close((err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve();
      });
      server = null;
    });

  return {
    baseUrl: `http://127.0.0.1:${address.port}/v1`,
    close,
    getRequestCount: () => requestCount,
  };
}

test("remote network failure shows mapped stream error code @smoke", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  await setRemoteSettingsWithUnreachableBaseUrl(request, auth.access_token);
  await seedBrowserAuth(page, auth);

  await page.goto("/");
  await ensureWorkbenchReady(page, auth);

  const composerInput = page.getByTestId("composer-input");
  const composerSend = page.getByTestId("composer-send");
  await composerInput.fill("trigger remote network error");
  await composerSend.click();

  const composerHint = page.getByTestId("composer-hint");
  await expect(composerHint).toContainText("remote_provider_network_error", {
    timeout: 20_000,
  });

  await composerInput.fill("after remote error can continue typing");
  await expect(composerSend).toBeEnabled({ timeout: 20_000 });
});

test("remote 401 maps to unauthorized stream error code", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const mockProvider = await startMockRemoteProvider({
    statusCode: 401,
    body: {
      error: {
        message: "Unauthorized by playwright mock provider",
      },
    },
  });
  try {
    await setRemoteSettings(request, auth.access_token, mockProvider.baseUrl);
    await seedBrowserAuth(page, auth);

    await page.goto("/");
    await ensureWorkbenchReady(page, auth);

    const composerInput = page.getByTestId("composer-input");
    const composerSend = page.getByTestId("composer-send");
    await composerInput.fill("trigger remote 401");
    await composerSend.click();

    const composerHint = page.getByTestId("composer-hint");
    await expect(composerHint).toContainText("remote_api_key_unauthorized", {
      timeout: 20_000,
    });
    await expect(composerHint).toContainText("HTTP 401", {
      timeout: 20_000,
    });
  } finally {
    await mockProvider.close();
  }
});

test("remote 429 maps to rate-limited stream error code", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const mockProvider = await startMockRemoteProvider({
    statusCode: 429,
    body: {
      error: {
        message: "Rate limit by playwright mock provider",
      },
    },
  });
  try {
    await setRemoteSettings(request, auth.access_token, mockProvider.baseUrl);
    await seedBrowserAuth(page, auth);

    await page.goto("/");
    await ensureWorkbenchReady(page, auth);

    const composerInput = page.getByTestId("composer-input");
    const composerSend = page.getByTestId("composer-send");
    await composerInput.fill("trigger remote 429");
    await composerSend.click();

    const composerHint = page.getByTestId("composer-hint");
    await expect(composerHint).toContainText("remote_provider_rate_limited", {
      timeout: 20_000,
    });
    await expect(composerHint).toContainText("HTTP 429", {
      timeout: 20_000,
    });
  } finally {
    await mockProvider.close();
  }
});

test("remote 503 maps to upstream stream error code", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const mockProvider = await startMockRemoteProvider({
    statusCode: 503,
    body: {
      error: {
        message: "Upstream unavailable by playwright mock provider",
      },
    },
  });
  try {
    await setRemoteSettings(request, auth.access_token, mockProvider.baseUrl);
    await seedBrowserAuth(page, auth);

    await page.goto("/");
    await ensureWorkbenchReady(page, auth);

    const composerInput = page.getByTestId("composer-input");
    const composerSend = page.getByTestId("composer-send");
    await composerInput.fill("trigger remote 503");
    await composerSend.click();

    const composerHint = page.getByTestId("composer-hint");
    await expect(composerHint).toContainText("remote_provider_upstream_error", {
      timeout: 20_000,
    });
    await expect(composerHint).toContainText("HTTP 503", {
      timeout: 20_000,
    });
  } finally {
    await mockProvider.close();
  }
});

test("remote cancel enters cooldown and recovers send", async ({
  page,
  request,
}) => {
  const auth = await registerViaApi(request);
  const mockProvider = await startMockRemoteStreamingProvider({
    tokenDelayMs: 150,
    tokenCount: 26,
  });
  try {
    await setRemoteSettings(request, auth.access_token, mockProvider.baseUrl);
    await seedBrowserAuth(page, auth);

    await page.goto("/");
    await ensureWorkbenchReady(page, auth);

    const composerInput = page.getByTestId("composer-input");
    const composerSend = page.getByTestId("composer-send");

    await composerInput.fill("trigger remote cancel cooldown flow");
    await composerSend.click();
    await expect
      .poll(() => mockProvider.getRequestCount(), {
        timeout: 20_000,
        intervals: [200, 400, 800],
      })
      .toBe(1);

    await openInspectorContextTab(page);
    const cancelButton = page
      .locator('[data-testid="inspector-task-cancel"]:visible')
      .first();
    await expect(cancelButton).toBeVisible({ timeout: 20_000 });
    await cancelButton.click();

    await expect(composerSend).not.toHaveClass(/ant-btn-loading/, {
      timeout: 4_000,
    });
    await expect(composerSend).toBeDisabled({ timeout: 4_000 });

    await composerInput.fill("blocked during cooldown");
    await composerInput.press("Enter");
    await page.waitForTimeout(350);
    expect(mockProvider.getRequestCount()).toBe(1);

    await expect(composerSend).toBeEnabled({ timeout: 12_000 });
    await composerInput.fill("after cooldown send works");
    await composerSend.click();

    await expect
      .poll(() => mockProvider.getRequestCount(), {
        timeout: 20_000,
        intervals: [200, 400, 800],
      })
      .toBe(2);
    await expect(
      page
        .locator("article.message-row.assistant")
        .filter({ hasText: "remote-stream-token-" })
        .first(),
    ).toBeVisible({ timeout: 20_000 });
  } finally {
    await mockProvider.close();
  }
});
