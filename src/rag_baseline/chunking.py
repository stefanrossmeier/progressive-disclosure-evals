from __future__ import annotations

import re
from dataclasses import dataclass

from progressive_disclosure.models import KnowledgeDocument

from .models import RagChunk


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class _Block:
    heading: str
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def _blocks(markdown: str) -> list[_Block]:
    """Turn Markdown into paragraph/list blocks annotated with their heading path."""

    heading_stack: dict[int, str] = {}
    blocks: list[_Block] = []
    paragraph: list[str] = []

    def heading_path() -> str:
        return " / ".join(heading_stack[level] for level in sorted(heading_stack))

    def flush() -> None:
        if not paragraph:
            return
        text = "\n".join(paragraph).strip()
        paragraph.clear()
        if text:
            blocks.append(_Block(heading=heading_path(), text=text))

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        match = _HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading_stack[level] = match.group(2).strip()
            for deeper in [key for key in heading_stack if key > level]:
                del heading_stack[deeper]
            continue
        if not line.strip():
            flush()
            continue
        paragraph.append(line)
    flush()
    return blocks


def _tail_words(text: str, count: int) -> str:
    if count <= 0:
        return ""
    words = text.split()
    return " ".join(words[-count:])


def _split_oversized_block(block: _Block, *, target_words: int, overlap_words: int) -> list[_Block]:
    words = block.text.split()
    if len(words) <= target_words:
        return [block]
    step = max(1, target_words - overlap_words)
    result: list[_Block] = []
    for start in range(0, len(words), step):
        piece = words[start : start + target_words]
        if not piece:
            break
        result.append(_Block(heading=block.heading, text=" ".join(piece)))
        if start + target_words >= len(words):
            break
    return result


def chunk_document(
    document: KnowledgeDocument,
    *,
    target_words: int = 320,
    overlap_words: int = 64,
) -> list[RagChunk]:
    """Create deterministic, Markdown-aware chunks for one knowledge document.

    Chunks pack neighboring paragraph/list blocks up to ``target_words`` while
    retaining the active heading path. Oversized blocks are split with a bounded
    word overlap. The indexed representation includes document metadata, but the
    answer model receives only the selected body excerpt plus source labels.
    """

    if target_words < 64:
        raise ValueError("target_words must be >= 64")
    if overlap_words < 0:
        raise ValueError("overlap_words must be >= 0")
    if overlap_words >= target_words:
        raise ValueError("overlap_words must be smaller than target_words")

    expanded: list[_Block] = []
    for block in _blocks(document.content):
        expanded.extend(
            _split_oversized_block(
                block,
                target_words=target_words,
                overlap_words=overlap_words,
            )
        )
    if not expanded:
        expanded = [_Block(heading="", text=document.content.strip())]

    min_flush_words = max(48, target_words // 2)
    packed: list[tuple[str, str]] = []
    current_parts: list[str] = []
    current_headings: list[str] = []
    current_words = 0

    def flush() -> str:
        nonlocal current_parts, current_headings, current_words
        text = "\n\n".join(part for part in current_parts if part).strip()
        if not text:
            return ""
        headings = list(dict.fromkeys(value for value in current_headings if value))
        heading = " | ".join(headings)
        packed.append((heading, text))
        overlap = _tail_words(text, overlap_words)
        current_parts = [overlap] if overlap else []
        current_headings = [headings[-1]] if overlap and headings else []
        current_words = len(overlap.split())
        return text

    for block in expanded:
        block_words = block.word_count
        if (
            current_parts
            and current_words >= min_flush_words
            and current_words + block_words > target_words
        ):
            flush()
        current_parts.append(block.text)
        if block.heading:
            current_headings.append(block.heading)
        current_words += block_words

    if current_parts:
        text = "\n\n".join(part for part in current_parts if part).strip()
        # Avoid an overlap-only final chunk.
        if text and (not packed or len(text.split()) > overlap_words):
            headings = list(dict.fromkeys(value for value in current_headings if value))
            packed.append((" | ".join(headings), text))

    chunks: list[RagChunk] = []
    for index, (heading, text) in enumerate(packed, start=1):
        chunk_id = f"{document.id}::c{index:03d}"
        search_lines = [
            f"Document ID: {document.id}",
            f"Title: {document.title}",
            f"Description: {document.description}",
            f"Path: {document.path}",
        ]
        if heading:
            search_lines.append(f"Section: {heading}")
        search_lines.extend(["", text])
        chunks.append(
            RagChunk(
                id=chunk_id,
                document_id=document.id,
                title=document.title,
                description=document.description,
                path=document.path,
                heading=heading,
                text=text,
                search_text="\n".join(search_lines),
            )
        )
    return chunks
