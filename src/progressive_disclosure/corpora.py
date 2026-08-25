from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CorpusSpec:
    name: str
    root: Path
    default_dataset: Path
    expected_documents: int
    require_version: bool = False
    ids_match_paths: bool = False
    activation_pattern: str | None = None
    reference_pattern: str | None = None
    minimum_cross_references: int = 0
    minimum_words_per_document: int = 0


CORPORA: dict[str, CorpusSpec] = {
    "northstar": CorpusSpec(
        name="northstar",
        root=Path("corpus/northstar-corpus"),
        default_dataset=Path("datasets/eval-v1.yaml"),
        expected_documents=40,
        require_version=True,
        ids_match_paths=True,
        activation_pattern=r"\buse (?:for|when)\b",
        reference_pattern=r"\b(?:operations|commercial|platform|governance)(?:\.[a-z0-9-]+){2,}\b",
    ),
    "tell-aster": CorpusSpec(
        name="tell-aster",
        root=Path("corpus/tell-aster"),
        default_dataset=Path("datasets/tell-aster-eval-v2.yaml"),
        expected_documents=80,
        activation_pattern=r"\b(?:use(?:ful)? (?:for|when)|consult (?:for|when))\b",
        reference_pattern=r"\bTA-(?:EXC|ARC|CER|ART|INS|BUR|ENV|DAT|CON|SUR|SYN)-\d{2}\b",
        minimum_cross_references=180,
        minimum_words_per_document=650,
    ),
}


def corpus_names() -> tuple[str, ...]:
    return tuple(CORPORA)


def get_corpus_spec(name: str) -> CorpusSpec:
    try:
        return CORPORA[name]
    except KeyError as exc:
        raise ValueError(f"unknown corpus {name!r}; choose one of: {', '.join(corpus_names())}") from exc


def corpus_name_from_dataset(data: dict[str, Any], *, default: str = "northstar") -> str:
    value = data.get("corpus", default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("dataset corpus must be a non-empty string")
    name = value.strip()
    get_corpus_spec(name)
    return name
