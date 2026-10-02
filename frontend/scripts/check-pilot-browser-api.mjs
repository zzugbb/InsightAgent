import { chromium } from "@playwright/test";

const [frontendAddress, expectedApiAddress] = process.argv.slice(2);
if (!frontendAddress || !expectedApiAddress) {
  console.error("usage: check-pilot-browser-api.mjs <frontend-url> <expected-api-url>");
  process.exit(2);
}

const frontendUrl = new URL(frontendAddress);
const expectedApiUrl = new URL(expectedApiAddress);
const expectedRequestUrl = new URL(`${expectedApiAddress}/api/auth/me`).href;
const expectedRequestPath = new URL(expectedRequestUrl).pathname;
let browser;

try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.addInitScript(() => {
    localStorage.setItem("insightagent.authToken", "pilot-browser-check-token");
  });
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin === frontendUrl.origin) {
      await route.continue();
      return;
    }
    if (url.origin === expectedApiUrl.origin && url.pathname === expectedRequestPath) {
      await route.fulfill({
        status: request.method() === "OPTIONS" ? 204 : 401,
        headers: {
          "access-control-allow-origin": frontendUrl.origin,
          "access-control-allow-methods": "GET, OPTIONS",
          "access-control-allow-headers": "authorization, content-type",
          "content-type": "application/json",
        },
        body: request.method() === "OPTIONS" ? "" : '{"detail":"invalid token"}',
      });
      return;
    }
    await route.abort();
  });

  const observedRequest = page.waitForRequest(
    (request) => request.method() === "GET" && new URL(request.url()).pathname.endsWith("/api/auth/me"),
    { timeout: 15000 },
  );
  await page.goto(frontendUrl.href, { waitUntil: "domcontentloaded" });
  const actualRequest = await observedRequest;
  if (actualRequest.url() !== expectedRequestUrl) {
    throw new Error("client API address does not match expected build value");
  }
  await page.getByRole("tablist").waitFor({ state: "visible", timeout: 8000 });
  console.log("PASS: browser client requested the expected API address");
} catch (error) {
  console.error(`FAIL: ${error instanceof Error ? error.message : "browser API check failed"}`);
  process.exitCode = 1;
} finally {
  await browser?.close();
}
