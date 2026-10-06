"""Shared lazy chunking; background requests have a bounded expansion budget."""

from collections.abc import Iterator

MAX_INGEST_JOB_CHUNKS = 5_000


def iter_text_chunks(text: str, *, chunk_size: int, chunk_overlap: int) -> Iterator[str]:
    src = text.strip()
    step = max(1, chunk_size - chunk_overlap)
    for start in range(0, len(src), step):
        end = min(len(src), start + chunk_size)
        chunk = src[start:end].strip()
        if chunk:
            yield chunk
        if end >= len(src):
            break


def validate_job_chunk_budget(documents, *, chunk_size: int, chunk_overlap: int) -> None:
    total = 0
    for document in documents:
        text = document["text"] if isinstance(document, dict) else document.text
        for _ in iter_text_chunks(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
            total += 1
            if total > MAX_INGEST_JOB_CHUNKS:
                raise ValueError("background import exceeds 5000 chunks; split documents or reduce overlap")
