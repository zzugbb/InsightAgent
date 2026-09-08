import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const FRONTEND_ROOT = path.resolve(import.meta.dirname, "..");

type PackageJson = {
  type?: string;
  engines?: {
    node?: string;
  };
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
};

async function readPackageJson(): Promise<PackageJson> {
  const packageJsonPath = path.join(FRONTEND_ROOT, "package.json");
  return JSON.parse(await readFile(packageJsonPath, "utf8")) as PackageJson;
}

test("frontend package declares ESM module mode for Node 24 test tooling", async () => {
  const packageJson = await readPackageJson();

  assert.equal(packageJson.type, "module");
});

test("frontend package keeps the Node 24 runtime floor explicit", async () => {
  const packageJson = await readPackageJson();

  assert.equal(packageJson.engines?.node, ">=24.0.0");
});

test("frontend Next runtime and lint tooling stay version-aligned", async () => {
  const packageJson = await readPackageJson();

  assert.equal(packageJson.dependencies?.next, "15.2.4");
  assert.equal(packageJson.devDependencies?.["eslint-config-next"], "^15.2.4");
});
