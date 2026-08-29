import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const FRONTEND_ROOT = path.resolve(import.meta.dirname, "..");
const MAX_SOURCE_LINES = 3000;
const SOURCE_EXTENSIONS = new Set([
  ".css",
  ".js",
  ".jsx",
  ".mjs",
  ".ts",
  ".tsx",
]);
const IGNORED_DIRECTORIES = new Set([
  ".next",
  "node_modules",
  "coverage",
  "dist",
  "build",
]);
const IGNORED_FILES = new Set(["package-lock.json"]);

async function collectSourceFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      if (entry.isDirectory()) {
        if (IGNORED_DIRECTORIES.has(entry.name)) {
          return [];
        }
        return collectSourceFiles(path.join(directory, entry.name));
      }
      if (!entry.isFile()) {
        return [];
      }
      if (IGNORED_FILES.has(entry.name)) {
        return [];
      }
      const filePath = path.join(directory, entry.name);
      if (!SOURCE_EXTENSIONS.has(path.extname(filePath))) {
        return [];
      }
      return [filePath];
    }),
  );
  return files.flat();
}

test("frontend source files stay below the size boundary", async () => {
  const sourceFiles = await collectSourceFiles(FRONTEND_ROOT);
  const oversized: string[] = [];
  for (const filePath of sourceFiles.sort()) {
    const lineCount = (await readFile(filePath, "utf8")).split("\n").length;
    if (lineCount > MAX_SOURCE_LINES) {
      oversized.push(
        `${path.relative(FRONTEND_ROOT, filePath)} has ${lineCount} lines`,
      );
    }
  }

  assert.deepEqual(oversized, []);
});
