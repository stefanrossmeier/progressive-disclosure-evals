from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentSummary:
    """Agent-visible metadata loaded before any document body."""

    id: str
    title: str
    description: str
    path: str


@dataclass(frozen=True)
class KnowledgeDocument:
    """A full document loaded only after the model explicitly selects it."""

    id: str
    title: str
    description: str
    path: str
    content: str
    references: tuple[str, ...] = ()
