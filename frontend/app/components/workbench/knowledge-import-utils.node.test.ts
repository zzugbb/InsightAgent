import assert from "node:assert/strict";
import test from "node:test";
import { KnowledgeImportError, readKnowledgeFiles, validImportKnowledgeBaseId, type ImportFile } from "./knowledge-import-utils.ts";

function file(name: string, text: string): ImportFile {
  const buffer = new TextEncoder().encode(text).buffer;
  return { name, size: buffer.byteLength, arrayBuffer: async () => buffer };
}
const error = (code: KnowledgeImportError["code"]) => (value: unknown) => value instanceof KnowledgeImportError && value.code === code;

test("UTF-8 BOM, Chinese and Markdown are decoded and keep stable filename identities", async () => {
  const docs = await readKnowledgeFiles([file("笔记.TXT", "\uFEFF 资料\n第二行 "), file("guide.md", "# Guide")]);
  assert.deepEqual(docs, [
    { text: "资料\n第二行", source: "笔记.TXT", document_id: "笔记.TXT" },
    { text: "# Guide", source: "guide.md", document_id: "guide.md" },
  ]);
  const revised = await readKnowledgeFiles([file("guide.md", "# Revised")]);
  assert.equal(revised[0].document_id, docs[1].document_id);
});
test("extension validation happens before reading any file", async () => {
  let reads = 0;
  const valid = { ...file("ok.txt", "text"), arrayBuffer: async () => { reads++; return new ArrayBuffer(0); } };
  await assert.rejects(readKnowledgeFiles([valid, file("bad.pdf", "text")]), error("format"));
  assert.equal(reads, 0);
});
test("selection count and duplicate names are bounded", async () => {
  await assert.rejects(readKnowledgeFiles([]), error("count"));
  await assert.rejects(readKnowledgeFiles(Array.from({ length: 21 }, (_, i) => file(`${i}.txt`, "a"))), error("count"));
  await assert.rejects(readKnowledgeFiles([file("a.md", "one"), file("a.md", "two")]), error("duplicate"));
});
test("filenames cannot contain paths, controls or exceed the document ID limit", async () => {
  for (const name of ["a/b.txt", "a\\b.txt", "a\u0000.txt", `${"a".repeat(125)}.txt`]) {
    await assert.rejects(readKnowledgeFiles([file(name, "text")]), error("name"));
  }
});
test("per-file and aggregate bytes are checked before allocating file contents", async () => {
  const oversized = { name: "a.txt", size: 256_001, arrayBuffer: async () => { throw Error("must not read"); } };
  await assert.rejects(readKnowledgeFiles([oversized]), error("size"));
  await assert.rejects(readKnowledgeFiles(Array.from({ length: 3 }, (_, i) => ({ ...oversized, name: `${i}.txt`, size: 200_000 }))), error("size"));
});
test("character limit counts Unicode code points like the API", async () => {
  assert.equal((await readKnowledgeFiles([file("emoji.txt", "😀".repeat(64_000))]))[0].text.length, 128_000);
  await assert.rejects(readKnowledgeFiles([file("long.txt", "a".repeat(64_001))]), error("size"));
});
test("invalid UTF-8, binary controls and blank content are rejected", async () => {
  await assert.rejects(readKnowledgeFiles([{ name: "bad.txt", size: 2, arrayBuffer: async () => new Uint8Array([0xc3, 0x28]).buffer }]), error("encoding"));
  await assert.rejects(readKnowledgeFiles([file("binary.md", "a\u0000b")]), error("encoding"));
  await assert.rejects(readKnowledgeFiles([file("empty.txt", " \n\t")] ), error("empty"));
});
test("read failures reject the entire batch and identify the failed file", async () => {
  await assert.rejects(readKnowledgeFiles([file("valid.txt", "ok"), {
    name: "missing.md", size: 1, arrayBuffer: async () => { throw Error("gone"); },
  }]), (value: unknown) => error("read")(value) && (value as KnowledgeImportError).fileName === "missing.md");
});
test("JSON escaping must stay within the backend payload budget", async () => {
  await assert.rejects(readKnowledgeFiles(Array.from({ length: 8 }, (_, i) => file(`${i}.txt`, '"'.repeat(64_000)))), error("size"));
});
test("target IDs are explicit and do not silently change into another collection", () => {
  for (const id of ["default", "shared-guide", "kb_1", "a", "a".repeat(48)]) assert.equal(validImportKnowledgeBaseId(id), true);
  for (const id of ["", "KB", "中文", "a b", "_kb", "kb-", "a".repeat(49)]) assert.equal(validImportKnowledgeBaseId(id), false);
});
