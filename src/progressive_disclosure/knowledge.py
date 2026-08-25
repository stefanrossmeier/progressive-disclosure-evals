from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .models import DocumentSummary, KnowledgeDocument


class KnowledgeBaseError(RuntimeError):
    pass


class InvalidCorpusError(KnowledgeBaseError):
    pass


class UnknownDocumentError(KnowledgeBaseError):
    def __init__(self, document_id: str):
        super().__init__(f"unknown knowledge document: {document_id}")
        self.document_id = document_id


class KnowledgeBase:
    """Filesystem-backed knowledge base with metadata-first disclosure.

    The directory hierarchy is organizational only. The agent initially sees the
    front-matter metadata for every leaf document, analogous to Agent Skills
    metadata or a repository table of contents. Full Markdown bodies are loaded
    only when explicitly requested.
    """

    def __init__(self, corpus_root: Path | str):
        self.corpus_root = Path(corpus_root)
        if not self.corpus_root.is_dir():
            raise InvalidCorpusError(f"corpus root does not exist: {self.corpus_root}")

        parsed: dict[str, tuple[DocumentSummary, str]] = {}
        for path in sorted(self.corpus_root.rglob("*.md")):
            metadata, body = self._parse_frontmatter(path)
            relative = path.relative_to(self.corpus_root)
            document_id = self._require_string(metadata.get("id"), path, "id")
            title = self._require_string(metadata.get("title"), path, "title")
            description = self._require_string(
                metadata.get("description"), path, "description"
            )
            version = metadata.get("version")
            if version is not None and not isinstance(version, int):
                raise InvalidCorpusError(f"{path}: version must be an integer when present")
            if not body.strip():
                raise InvalidCorpusError(f"{path}: document body is empty")

            # Document IDs are stable corpus metadata. Directory structure is organizational
            # only and must not constrain corpora to one naming convention.
            if document_id in parsed:
                raise InvalidCorpusError(f"duplicate document id: {document_id}")

            parsed[document_id] = (
                DocumentSummary(
                    id=document_id,
                    title=title,
                    description=description,
                    path=relative.as_posix(),
                ),
                body,
            )

        if not parsed:
            raise InvalidCorpusError("corpus contains no Markdown documents")

        all_ids = set(parsed)
        self._documents: dict[str, KnowledgeDocument] = {}
        for document_id, (summary, body) in parsed.items():
            references = tuple(
                sorted(other_id for other_id in all_ids if other_id != document_id and other_id in body)
            )
            self._documents[document_id] = KnowledgeDocument(
                id=summary.id,
                title=summary.title,
                description=summary.description,
                path=summary.path,
                content=body,
                references=references,
            )

    @property
    def document_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._documents))

    def catalog(self) -> tuple[DocumentSummary, ...]:
        return tuple(
            DocumentSummary(
                id=doc.id,
                title=doc.title,
                description=doc.description,
                path=doc.path,
            )
            for doc in sorted(self._documents.values(), key=lambda item: item.id)
        )

    def read(self, document_id: str) -> KnowledgeDocument:
        try:
            return self._documents[document_id]
        except KeyError as exc:
            raise UnknownDocumentError(document_id) from exc

    def __contains__(self, document_id: object) -> bool:
        return isinstance(document_id, str) and document_id in self._documents

    @property
    def full_content_characters(self) -> int:
        return sum(len(document.content) for document in self._documents.values())

    @property
    def catalog_characters(self) -> int:
        return sum(
            len(item.id) + len(item.title) + len(item.description) + len(item.path)
            for item in self.catalog()
        )

    @staticmethod
    def _parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            raise InvalidCorpusError(f"{path}: missing YAML front matter")

        match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, flags=re.DOTALL)
        if not match:
            raise InvalidCorpusError(f"{path}: malformed YAML front matter")

        try:
            metadata = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            raise InvalidCorpusError(f"{path}: invalid YAML: {exc}") from exc
        if not isinstance(metadata, dict):
            raise InvalidCorpusError(f"{path}: front matter must be a mapping")
        return metadata, match.group(2)

    @staticmethod
    def _require_string(value: Any, path: Path, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise InvalidCorpusError(f"{path}: {field} must be a non-empty string")
        return value.strip()
