import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const FRONTEND_ROOT = path.resolve(import.meta.dirname, "..");
const EXPECTED_NEXT_VERSION = "15.5.25";
const EXPECTED_ESLINT_VERSION = "9.39.5";
const EXPECTED_AUDIT_SAFE_LOCK_VERSIONS = {
  "node_modules/@eslint/plugin-kit": "0.4.1",
  "node_modules/@humanfs/node": "0.16.8",
  "node_modules/brace-expansion": "1.1.21",
  "node_modules/@typescript-eslint/typescript-estree/node_modules/brace-expansion":
    "5.0.12",
  "node_modules/nanoid": "3.3.19",
} as const;

type PackageJson = {
  type?: string;
  scripts?: Record<string, string>;
  engines?: {
    node?: string;
  };
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
};

type PackageLock = {
  packages?: Record<
    string,
    {
      version?: string;
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    }
  >;
};

async function readPackageJson(): Promise<PackageJson> {
  const packageJsonPath = path.join(FRONTEND_ROOT, "package.json");
  return JSON.parse(await readFile(packageJsonPath, "utf8")) as PackageJson;
}

async function readPackageLock(): Promise<PackageLock> {
  const packageLockPath = path.join(FRONTEND_ROOT, "package-lock.json");
  return JSON.parse(await readFile(packageLockPath, "utf8")) as PackageLock;
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
  const nextVersion = packageJson.dependencies?.next;

  assert.equal(nextVersion, EXPECTED_NEXT_VERSION);
  assert.equal(packageJson.devDependencies?.["eslint-config-next"], nextVersion);
});

test("frontend lint uses the explicit ESLint CLI configuration", async () => {
  const packageJson = await readPackageJson();
  const eslintConfig = await readFile(
    path.join(FRONTEND_ROOT, "eslint.config.mjs"),
    "utf8",
  );

  assert.equal(packageJson.scripts?.lint, "eslint .");
  assert.match(eslintConfig, /next\/core-web-vitals/);
  assert.match(eslintConfig, /next\/typescript/);
  assert.match(eslintConfig, /\.next\/\*\*/);
});

test("frontend lockfile keeps Next runtime and lint tooling exactly aligned", async () => {
  const packageJson = await readPackageJson();
  const packageLock = await readPackageLock();
  const nextVersion = packageJson.dependencies?.next;
  const lockRoot = packageLock.packages?.[""];

  assert.equal(lockRoot?.dependencies?.next, nextVersion);
  assert.equal(lockRoot?.devDependencies?.["eslint-config-next"], nextVersion);
  assert.equal(packageLock.packages?.["node_modules/next"]?.version, nextVersion);
  assert.equal(
    packageLock.packages?.["node_modules/eslint-config-next"]?.version,
    nextVersion,
  );
});

test("frontend lockfile keeps fixable audit dependencies on safe patches", async () => {
  const packageJson = await readPackageJson();
  const packageLock = await readPackageLock();
  const lockRoot = packageLock.packages?.[""];

  assert.equal(packageJson.devDependencies?.eslint, EXPECTED_ESLINT_VERSION);
  assert.equal(lockRoot?.devDependencies?.eslint, EXPECTED_ESLINT_VERSION);
  assert.equal(
    packageLock.packages?.["node_modules/eslint"]?.version,
    EXPECTED_ESLINT_VERSION,
  );

  for (const [packagePath, expectedVersion] of Object.entries(
    EXPECTED_AUDIT_SAFE_LOCK_VERSIONS,
  )) {
    assert.equal(
      packageLock.packages?.[packagePath]?.version,
      expectedVersion,
      `${packagePath} must stay on its audited safe patch`,
    );
  }
});
