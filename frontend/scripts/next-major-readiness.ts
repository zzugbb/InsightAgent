import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

type PackageJson = {
  engines?: { node?: string };
  scripts?: Record<string, string>;
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
};

type SourceFile = {
  path: string;
  content: string;
};

type ReadinessInput = {
  packageJson: PackageJson;
  eslintConfig: string;
  nextConfig: string;
  sourceFiles: SourceFile[];
};

type Finding = {
  id: string;
  status?: "pass" | "fail";
  detail: string;
};

type ReadinessReport = {
  schemaVersion: 1;
  targetMajor: 16;
  status: "ready" | "ready_with_actions" | "blocked";
  prerequisites: Finding[];
  actions: Finding[];
  blockers: Finding[];
};

function versionAtLeast(value: string | undefined, minimum: [number, number]): boolean {
  const match = value?.match(/(\d+)\.(\d+)/);
  if (!match) {
    return false;
  }
  const current: [number, number] = [Number(match[1]), Number(match[2])];
  return current[0] > minimum[0]
    || (current[0] === minimum[0] && current[1] >= minimum[1]);
}

function majorVersion(value: string | undefined): number | undefined {
  const match = value?.match(/\d+/);
  return match ? Number(match[0]) : undefined;
}

function prerequisite(id: string, pass: boolean, detail: string): Finding {
  return { id, status: pass ? "pass" : "fail", detail };
}

export function evaluateNextMajorReadiness(input: ReadinessInput): ReadinessReport {
  const { packageJson, eslintConfig, nextConfig, sourceFiles } = input;
  const applicationSourceFiles = sourceFiles.filter(
    ({ path: filePath }) => !/\.(?:node\.)?(?:test|spec)\.[cm]?[jt]sx?$/.test(filePath),
  );
  const prerequisites = [
    prerequisite(
      "node-runtime-floor",
      versionAtLeast(packageJson.engines?.node, [20, 9]),
      "Next 16 requires Node.js 20.9 or newer.",
    ),
    prerequisite(
      "typescript-floor",
      versionAtLeast(packageJson.devDependencies?.typescript, [5, 1]),
      "Next 16 requires TypeScript 5.1 or newer.",
    ),
    prerequisite(
      "eslint-cli",
      packageJson.scripts?.lint === "eslint .",
      "Next 16 removes next lint; lint must use the ESLint CLI.",
    ),
  ];

  const actions: Finding[] = [];
  const dependencyAlignmentComplete =
    majorVersion(packageJson.dependencies?.next) === 16
    && majorVersion(packageJson.dependencies?.react) === 19
    && versionAtLeast(packageJson.dependencies?.react, [19, 2])
    && packageJson.dependencies?.react === packageJson.dependencies?.["react-dom"]
    && majorVersion(packageJson.devDependencies?.["eslint-config-next"]) === 16;
  if (!dependencyAlignmentComplete) {
    actions.push({
      id: "next-16-dependency-alignment",
      detail: "Upgrade Next, eslint-config-next, React, React DOM, and React types together.",
    });
  }

  const nativeFlatConfig =
    !eslintConfig.includes("FlatCompat")
    && eslintConfig.includes("eslint-config-next/core-web-vitals")
    && eslintConfig.includes("eslint-config-next/typescript");
  if (!nativeFlatConfig) {
    actions.push({
      id: "native-eslint-flat-config",
      detail: "Replace the Next 15 compatibility adapter after eslint-config-next exposes flat arrays.",
    });
  }

  if (!packageJson.scripts?.build?.includes("--turbopack")) {
    actions.push({
      id: "turbopack-build-verification",
      detail: "Verify the production build with Turbopack before accepting the Next 16 default.",
    });
  }

  const blockers: Finding[] = prerequisites
    .filter(({ status }) => status === "fail")
    .map(({ id, detail }) => ({ id, detail }));

  if (/\bwebpack\s*(?::|\()/.test(nextConfig)) {
    blockers.push({
      id: "custom-webpack-config",
      detail: "Migrate or explicitly retain custom webpack behavior before Turbopack becomes the default.",
    });
  }

  if (applicationSourceFiles.some(
    ({ path: filePath }) => /(^|\/)middleware\.[cm]?[jt]sx?$/.test(filePath),
  )) {
    blockers.push({
      id: "legacy-middleware-convention",
      detail: "Review and migrate the middleware convention to proxy.",
    });
  }

  const hasSyncRequestApi = applicationSourceFiles.some(({ content }) => {
    if (!/from\s+["']next\/headers["']/.test(content)) {
      return false;
    }
    const withoutAwaitedCalls = content.replace(
      /\bawait\s+(?:cookies|headers|draftMode)\s*\(/g,
      "",
    );
    return /\b(?:cookies|headers|draftMode)\s*\(/.test(withoutAwaitedCalls);
  });
  if (hasSyncRequestApi) {
    blockers.push({
      id: "sync-request-api-review",
      detail: "Migrate synchronous cookies, headers, or draftMode access to the async APIs.",
    });
  }

  return {
    schemaVersion: 1,
    targetMajor: 16,
    status: blockers.length > 0
      ? "blocked"
      : actions.length > 0
        ? "ready_with_actions"
        : "ready",
    prerequisites,
    actions,
    blockers,
  };
}

async function collectSourceFiles(root: string): Promise<SourceFile[]> {
  const files: SourceFile[] = [];

  async function visit(directory: string): Promise<void> {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const absolutePath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        await visit(absolutePath);
      } else if (/\.[cm]?[jt]sx?$/.test(entry.name)) {
        files.push({
          path: path.relative(root, absolutePath),
          content: await readFile(absolutePath, "utf8"),
        });
      }
    }
  }

  await visit(path.join(root, "app"));
  for (const entry of await readdir(root, { withFileTypes: true })) {
    if (entry.isFile() && /^middleware\.[cm]?[jt]sx?$/.test(entry.name)) {
      files.push({ path: entry.name, content: await readFile(path.join(root, entry.name), "utf8") });
    }
  }
  return files;
}

async function readProjectReport(root: string): Promise<ReadinessReport> {
  const packageJson = JSON.parse(
    await readFile(path.join(root, "package.json"), "utf8"),
  ) as PackageJson;
  return evaluateNextMajorReadiness({
    packageJson,
    eslintConfig: await readFile(path.join(root, "eslint.config.mjs"), "utf8"),
    nextConfig: await readFile(path.join(root, "next.config.ts"), "utf8"),
    sourceFiles: await collectSourceFiles(root),
  });
}

const invokedPath = process.argv[1] ? pathToFileURL(path.resolve(process.argv[1])).href : "";
if (import.meta.url === invokedPath) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  const report = await readProjectReport(root);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  if (report.status === "blocked") {
    process.exitCode = 1;
  }
}
