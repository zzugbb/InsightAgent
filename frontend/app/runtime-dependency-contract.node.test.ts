import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const FRONTEND_ROOT = path.resolve(import.meta.dirname, "..");
const EXPECTED_NEXT_VERSION = "16.3.5";
const EXPECTED_REACT_VERSION = "19.2.8";
const EXPECTED_REACT_TYPES_VERSION = "19.2.18";
const EXPECTED_REACT_DOM_TYPES_VERSION = "19.2.7";
const EXPECTED_ESLINT_VERSION = "9.39.5";
const EXPECTED_AUDIT_SAFE_LOCK_VERSIONS = {
  "node_modules/@eslint/plugin-kit": "0.4.1",
  "node_modules/@humanfs/node": "0.16.8",
  "node_modules/brace-expansion": "5.0.12",
  "node_modules/nanoid": "3.3.19",
  "node_modules/postcss": "8.5.23",
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

type TypeScriptConfig = {
  compilerOptions?: { jsx?: string };
  include?: string[];
  exclude?: string[];
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

test("Next 16 production typecheck excludes Node test fixtures", async () => {
  const tsConfig = JSON.parse(
    await readFile(path.join(FRONTEND_ROOT, "tsconfig.json"), "utf8"),
  ) as TypeScriptConfig;

  assert.equal(tsConfig.compilerOptions?.jsx, "react-jsx");
  assert.ok(tsConfig.include?.includes(".next/dev/types/**/*.ts"));
  assert.ok(tsConfig.exclude?.includes("**/*.node.test.ts"));
  assert.ok(tsConfig.exclude?.includes("**/*.type.test.ts"));
});

test("Next 16 frontend agent instructions point to bundled versioned docs", async () => {
  const agentInstructions = await readFile(
    path.join(FRONTEND_ROOT, "AGENTS.md"),
    "utf8",
  );

  assert.match(agentInstructions, /BEGIN:nextjs-agent-rules/);
  assert.match(agentInstructions, /node_modules\/next\/dist\/docs\//);
  assert.match(agentInstructions, /\.\.\/AGENTS\.md/);
  assert.match(agentInstructions, /END:nextjs-agent-rules/);
});

test("frontend Next 16 runtime, React, types, and lint tooling stay version-aligned", async () => {
  const packageJson = await readPackageJson();
  const nextVersion = packageJson.dependencies?.next;

  assert.equal(nextVersion, EXPECTED_NEXT_VERSION);
  assert.equal(packageJson.devDependencies?.["eslint-config-next"], nextVersion);
  assert.equal(packageJson.dependencies?.react, EXPECTED_REACT_VERSION);
  assert.equal(packageJson.dependencies?.["react-dom"], EXPECTED_REACT_VERSION);
  assert.equal(
    packageJson.devDependencies?.["@types/react"],
    EXPECTED_REACT_TYPES_VERSION,
  );
  assert.equal(
    packageJson.devDependencies?.["@types/react-dom"],
    EXPECTED_REACT_DOM_TYPES_VERSION,
  );
  assert.equal(packageJson.devDependencies?.eslint, EXPECTED_ESLINT_VERSION);
  assert.equal(packageJson.devDependencies?.["@eslint/eslintrc"], undefined);
});

test("frontend lint uses the native Next 16 flat configuration", async () => {
  const packageJson = await readPackageJson();
  const eslintConfig = await readFile(
    path.join(FRONTEND_ROOT, "eslint.config.mjs"),
    "utf8",
  );

  assert.equal(packageJson.scripts?.lint, "eslint .");
  assert.match(eslintConfig, /eslint-config-next\/core-web-vitals/);
  assert.match(eslintConfig, /eslint-config-next\/typescript/);
  assert.match(eslintConfig, /defineConfig/);
  assert.match(eslintConfig, /globalIgnores/);
  assert.match(eslintConfig, /\.next\/\*\*/);
  assert.doesNotMatch(eslintConfig, /["']react-hooks\/refs["']:\s*["']off["']/);
  assert.doesNotMatch(eslintConfig, /FlatCompat/);
  assert.doesNotMatch(eslintConfig, /@eslint\/eslintrc/);
});

test("React Compiler state-effect hold is scoped to the remaining migration files", async () => {
  const configModule = await import(
    pathToFileURL(path.join(FRONTEND_ROOT, "eslint.config.mjs")).href
  ) as {
    default: Array<{
      files?: string[];
      rules?: Record<string, unknown>;
    }>;
  };
  const scopedHolds = configModule.default
    .filter(
      (entry) => entry.rules?.["react-hooks/set-state-in-effect"] === "off",
    )
    .flatMap((entry) => entry.files ?? ["<global>"]);

  assert.deepEqual(scopedHolds, [
    "app/components/workbench/index.tsx",
    "app/components/workbench/knowledge-base-governance-modal.tsx",
    "app/components/workbench/model-settings-modal.tsx",
    "app/components/workbench/runtime-debug-modal.tsx",
    "app/components/workbench/sidebar-settings-menu.tsx",
    "app/components/workbench/task-center.tsx",
    "lib/preferences-context.tsx",
  ]);
});

test("frontend lockfile keeps Next runtime and lint tooling exactly aligned", async () => {
  const packageJson = await readPackageJson();
  const packageLock = await readPackageLock();
  const nextVersion = packageJson.dependencies?.next;
  const lockRoot = packageLock.packages?.[""];

  assert.equal(lockRoot?.dependencies?.next, nextVersion);
  assert.equal(lockRoot?.dependencies?.react, EXPECTED_REACT_VERSION);
  assert.equal(lockRoot?.dependencies?.["react-dom"], EXPECTED_REACT_VERSION);
  assert.equal(lockRoot?.devDependencies?.["eslint-config-next"], nextVersion);
  assert.equal(
    lockRoot?.devDependencies?.["@types/react"],
    EXPECTED_REACT_TYPES_VERSION,
  );
  assert.equal(
    lockRoot?.devDependencies?.["@types/react-dom"],
    EXPECTED_REACT_DOM_TYPES_VERSION,
  );
  assert.equal(lockRoot?.devDependencies?.["@eslint/eslintrc"], undefined);
  assert.equal(packageLock.packages?.["node_modules/next"]?.version, nextVersion);
  assert.equal(
    packageLock.packages?.["node_modules/react"]?.version,
    EXPECTED_REACT_VERSION,
  );
  assert.equal(
    packageLock.packages?.["node_modules/react-dom"]?.version,
    EXPECTED_REACT_VERSION,
  );
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
