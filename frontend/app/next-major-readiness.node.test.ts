import assert from "node:assert/strict";
import test from "node:test";

import { evaluateNextMajorReadiness } from "../scripts/next-major-readiness.ts";

const BASE_INPUT = {
  packageJson: {
    engines: { node: ">=24.0.0" },
    scripts: { build: "next build", lint: "eslint ." },
    dependencies: {
      next: "15.5.25",
      react: "19.0.0",
      "react-dom": "19.0.0",
    },
    devDependencies: {
      "eslint-config-next": "15.5.25",
      typescript: "5.8.2",
    },
  },
  eslintConfig: 'import { FlatCompat } from "@eslint/eslintrc";',
  nextConfig: "const nextConfig = { reactStrictMode: true };",
  sourceFiles: [],
};

test("Next 16 preflight separates satisfied prerequisites from migration actions", () => {
  const report = evaluateNextMajorReadiness(BASE_INPUT);

  assert.equal(report.schemaVersion, 1);
  assert.equal(report.targetMajor, 16);
  assert.equal(report.status, "ready_with_actions");
  assert.deepEqual(report.blockers, []);
  assert.deepEqual(
    report.prerequisites.map(({ id, status }) => ({ id, status })),
    [
      { id: "node-runtime-floor", status: "pass" },
      { id: "typescript-floor", status: "pass" },
      { id: "eslint-cli", status: "pass" },
    ],
  );
  assert.deepEqual(
    report.actions.map(({ id }) => id),
    [
      "next-16-dependency-alignment",
      "native-eslint-flat-config",
      "turbopack-build-verification",
    ],
  );
});

test("Next 16 preflight blocks known project-level breaking surfaces", () => {
  const report = evaluateNextMajorReadiness({
    ...BASE_INPUT,
    nextConfig: "const nextConfig = { webpack(config) { return config; } };",
    sourceFiles: [
      { path: "middleware.ts", content: "export function middleware() {}" },
      {
        path: "app/page.tsx",
        content: 'import { cookies } from "next/headers"; cookies();',
      },
    ],
  });

  assert.equal(report.status, "blocked");
  assert.deepEqual(
    report.blockers.map(({ id }) => id),
    [
      "custom-webpack-config",
      "legacy-middleware-convention",
      "sync-request-api-review",
    ],
  );
});

test("Next 16 preflight ignores request API fixtures in test sources", () => {
  const report = evaluateNextMajorReadiness({
    ...BASE_INPUT,
    sourceFiles: [
      {
        path: "app/request-api.node.test.ts",
        content: 'import { cookies } from "next/headers"; cookies();',
      },
    ],
  });

  assert.equal(report.status, "ready_with_actions");
  assert.deepEqual(report.blockers, []);
});

test("Next 16 preflight accepts awaited request APIs across whitespace", () => {
  const report = evaluateNextMajorReadiness({
    ...BASE_INPUT,
    sourceFiles: [
      {
        path: "app/server-page.tsx",
        content: 'import { cookies } from "next/headers"; const store = await\n  cookies();',
      },
    ],
  });

  assert.equal(report.status, "ready_with_actions");
  assert.deepEqual(report.blockers, []);
});
