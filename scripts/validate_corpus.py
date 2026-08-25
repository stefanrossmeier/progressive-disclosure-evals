#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from progressive_disclosure.corpora import CORPORA, CorpusSpec, get_corpus_spec


@dataclass(frozen=True)
class ValidationError:
    source: str
    message: str

    def __str__(self) -> str:
        return f"{self.source}: {self.message}"


@dataclass(frozen=True)
class CorpusStats:
    documents: int
    metadata_entries: int
    cross_references: int
    legacy_indexes: int
    words: int


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("document does not start with YAML front matter")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, flags=re.DOTALL)
    if not match:
        raise ValueError("could not parse YAML front matter")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError("front matter must parse to a mapping")
    return metadata, match.group(2)


def validate_corpus(root: Path, spec: CorpusSpec | None = None) -> tuple[list[ValidationError], CorpusStats]:
    errors: list[ValidationError] = []
    if not root.is_dir():
        return [ValidationError(str(root), "corpus root does not exist")], CorpusStats(0, 0, 0, 0, 0)

    paths = sorted(root.rglob("*.md"))
    legacy_indexes = sorted(root.rglob("_index.yaml"))
    for path in legacy_indexes:
        errors.append(ValidationError(path.relative_to(root).as_posix(), "legacy _index.yaml is not supported"))

    if spec and len(paths) != spec.expected_documents:
        errors.append(ValidationError(str(root), f"expected {spec.expected_documents} Markdown documents, found {len(paths)}"))

    ids: dict[str, Path] = {}
    bodies: dict[str, str] = {}
    total_words = 0
    for path in paths:
        rel = path.relative_to(root)
        source = rel.as_posix()
        try:
            metadata, body = parse_frontmatter(path)
        except Exception as exc:
            errors.append(ValidationError(source, str(exc)))
            continue

        missing = {"id", "title", "description"} - metadata.keys()
        if missing:
            errors.append(ValidationError(source, "missing front matter fields: " + ", ".join(sorted(missing))))
            continue

        document_id = metadata.get("id")
        title = metadata.get("title")
        description = metadata.get("description")
        version = metadata.get("version")
        if not isinstance(document_id, str) or not document_id.strip():
            errors.append(ValidationError(source, "id must be a non-empty string"))
            continue
        document_id = document_id.strip()
        if document_id in ids:
            errors.append(ValidationError(source, f"duplicate id {document_id!r}"))
        ids[document_id] = path

        if spec and spec.ids_match_paths:
            expected_id = ".".join(rel.with_suffix("").parts)
            if document_id != expected_id:
                errors.append(ValidationError(source, f"id {document_id!r} does not match path-derived id {expected_id!r}"))
        if spec and spec.require_version and not isinstance(version, int):
            errors.append(ValidationError(source, "version must be an integer"))
        elif version is not None and not isinstance(version, int):
            errors.append(ValidationError(source, "version must be an integer when present"))
        if not isinstance(title, str) or not title.strip():
            errors.append(ValidationError(source, "title must be a non-empty string"))
        if not isinstance(description, str) or not description.strip():
            errors.append(ValidationError(source, "description must be a non-empty string"))
        elif len(description) > 1024:
            errors.append(ValidationError(source, "description exceeds 1024 characters"))
        elif spec and spec.activation_pattern and not re.search(spec.activation_pattern, description, flags=re.IGNORECASE):
            errors.append(ValidationError(source, "description does not contain a recognizable activation clause"))
        if not body.strip():
            errors.append(ValidationError(source, "document body is empty"))
        bodies[document_id] = body
        words = len(re.findall(r"\b[\w’'-]+\b", body))
        total_words += words
        if spec and spec.minimum_words_per_document and words < spec.minimum_words_per_document:
            errors.append(ValidationError(source, f"document too short: {words} words; expected at least {spec.minimum_words_per_document}"))

    reference_count = 0
    if spec and spec.reference_pattern:
        pattern = re.compile(spec.reference_pattern)
        known = set(ids)
        for document_id, body in bodies.items():
            for candidate in pattern.findall(body):
                if candidate == document_id:
                    continue
                if candidate not in known:
                    errors.append(ValidationError(ids[document_id].relative_to(root).as_posix(), f"references unknown document id {candidate!r}"))
                else:
                    reference_count += 1
        if reference_count < spec.minimum_cross_references:
            errors.append(ValidationError(str(root), f"expected at least {spec.minimum_cross_references} explicit cross references, found {reference_count}"))
    else:
        known = set(ids)
        for document_id, body in bodies.items():
            reference_count += sum(1 for candidate in known if candidate != document_id and candidate in body)

    return errors, CorpusStats(len(paths), len(ids), reference_count, len(legacy_indexes), total_words)


def print_result(name: str, errors: list[ValidationError], stats: CorpusStats) -> bool:
    if errors:
        print(f"\nCorpus validation FAILED [{name}] with {len(errors)} error(s):\n")
        for error in errors:
            print(f"  - {error}")
        return False
    print(f"\nCorpus validation PASSED [{name}]\n")
    print(f"  Documents:           {stats.documents}")
    print(f"  Metadata entries:    {stats.metadata_entries}")
    print(f"  Cross references:    {stats.cross_references}")
    print(f"  Legacy indexes:      {stats.legacy_indexes}")
    print(f"  Body words:          {stats.words}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate progressive-disclosure knowledge corpora.")
    parser.add_argument("--corpus", choices=tuple(CORPORA), default="northstar")
    parser.add_argument("--all", action="store_true", help="Validate every registered corpus")
    parser.add_argument("--corpus-root", type=Path, help="Validate an explicit root using generic checks")
    args = parser.parse_args()

    if args.all and args.corpus_root:
        parser.error("--all and --corpus-root cannot be combined")

    targets: list[tuple[str, Path, CorpusSpec | None]]
    if args.corpus_root:
        targets = [("custom", args.corpus_root, None)]
    elif args.all:
        targets = [(name, spec.root, spec) for name, spec in CORPORA.items()]
    else:
        spec = get_corpus_spec(args.corpus)
        targets = [(spec.name, spec.root, spec)]

    ok = True
    for name, root, spec in targets:
        errors, stats = validate_corpus(root, spec)
        ok = print_result(name, errors, stats) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
