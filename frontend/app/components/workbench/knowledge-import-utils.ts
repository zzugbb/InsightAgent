export type ImportDocument = { text: string; source: string; document_id: string };
export type ImportFile = { name: string; size: number; arrayBuffer: () => Promise<ArrayBuffer> };
export type ImportFileError = "format" | "encoding" | "empty" | "size" | "count" | "name" | "duplicate" | "read";

export class KnowledgeImportError extends Error {
  code: ImportFileError;
  fileName: string;
  constructor(code: ImportFileError, fileName = "") {
    super(code);
    this.code = code;
    this.fileName = fileName;
  }
}

// Conservative browser limits also leave room for JSON escaping in the 1 MB API payload.
const MAX_FILE_BYTES = 256_000;
const MAX_TOTAL_BYTES = 512_000;
const MAX_FILES = 20;

export function validImportKnowledgeBaseId(value: string): boolean {
  return /^[a-z0-9](?:[a-z0-9_-]{0,46}[a-z0-9])?$/.test(value);
}

export async function readKnowledgeFiles(files: readonly ImportFile[]): Promise<ImportDocument[]> {
  if (files.length === 0 || files.length > MAX_FILES) throw new KnowledgeImportError("count");
  const names = new Set<string>();
  let bytes = 0;
  for (const file of files) {
    if (!/\.(txt|md|markdown)$/i.test(file.name)) throw new KnowledgeImportError("format", file.name);
    if (Array.from(file.name).length > 128 || /[\x00-\x1f\x7f/\\]/.test(file.name)) {
      throw new KnowledgeImportError("name", file.name);
    }
    if (names.has(file.name)) throw new KnowledgeImportError("duplicate", file.name);
    names.add(file.name);
    bytes += file.size;
    if (file.size > MAX_FILE_BYTES || bytes > MAX_TOTAL_BYTES) throw new KnowledgeImportError("size", file.name);
  }
  const documents: ImportDocument[] = [];
  for (const file of files) {
    let buffer: ArrayBuffer;
    try { buffer = await file.arrayBuffer(); }
    catch { throw new KnowledgeImportError("read", file.name); }
    let text: string;
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(buffer).trim(); }
    catch { throw new KnowledgeImportError("encoding", file.name); }
    if (/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text)) throw new KnowledgeImportError("encoding", file.name);
    if (!text) throw new KnowledgeImportError("empty", file.name);
    if (Array.from(text).length > 64_000) throw new KnowledgeImportError("size", file.name);
    documents.push({ text, source: file.name, document_id: file.name });
  }
  // JSON's escaping can enlarge otherwise valid UTF-8 text (e.g. tabs and quotes).
  if (new TextEncoder().encode(JSON.stringify({ documents })).length > 900_000) {
    throw new KnowledgeImportError("size");
  }
  return documents;
}
