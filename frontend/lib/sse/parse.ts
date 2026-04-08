export function parseSseBlocks(chunk: string): { remainder: string; blocks: string[] } {
  const parts = chunk.split(/\r?\n\r?\n/);
  const remainder = parts.pop() ?? "";
  return { remainder, blocks: parts.filter(Boolean) };
}

export function parseSseBlock(block: string): { event: string; data: string } | null {
  let eventName = "message";
  const dataLines: string[] = [];
  for (const raw of block.split(/\r?\n/)) {
    const line = raw.replace(/^\uFEFF/, "");
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trimStart();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return { event: eventName, data: dataLines.join("\n") };
}
