import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
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
      eslint: "9.39.5",
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
      "eslint-10-plugin-compatibility",
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

test("frontend keeps the Next 16 Turbopack default with an explicit webpack fallback", async () => {
  const packageJson = JSON.parse(
    await readFile(path.resolve(import.meta.dirname, "..", "package.json"), "utf8"),
  ) as { scripts?: Record<string, string> };

  assert.equal(packageJson.scripts?.build, "next build");
  assert.equal(packageJson.scripts?.["build:webpack"], "next build --webpack");
  assert.equal(packageJson.scripts?.["build:turbopack"], undefined);
});

test("Next 16 preflight accepts a dedicated Turbopack production build", () => {
  const report = evaluateNextMajorReadiness({
    ...BASE_INPUT,
    packageJson: {
      ...BASE_INPUT.packageJson,
      scripts: {
        ...BASE_INPUT.packageJson.scripts,
        "build:turbopack": "next build --turbopack",
      },
    },
  });

  assert.deepEqual(
    report.actions.map(({ id }) => id),
    [
      "next-16-dependency-alignment",
      "native-eslint-flat-config",
      "eslint-10-plugin-compatibility",
    ],
  );
});

test("real frontend reaches Next 16 with an explicit ESLint 10 compatibility hold", async () => {
  const frontendRoot = path.resolve(import.meta.dirname, "..");
  const packageJson = JSON.parse(
    await readFile(path.join(frontendRoot, "package.json"), "utf8"),
  );
  const report = evaluateNextMajorReadiness({
    packageJson,
    eslintConfig: await readFile(path.join(frontendRoot, "eslint.config.mjs"), "utf8"),
    nextConfig: await readFile(path.join(frontendRoot, "next.config.ts"), "utf8"),
    sourceFiles: [],
  });

  assert.equal(report.status, "ready_with_actions");
  assert.deepEqual(
    report.actions.map(({ id }) => id),
    ["eslint-10-plugin-compatibility", "react-compiler-lint-migration"],
  );
  assert.deepEqual(report.blockers, []);
});
