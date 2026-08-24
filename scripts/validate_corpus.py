#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


EXPECTED_DOCUMENT_COUNT = 40
REQUIRED_FRONTMATTER_FIELDS = {"id", "title", "description", "version"}


@dataclass
class ValidationError:
    source: str
    message: str

    def __str__(self) -> str:
        return f"{self.source}: {self.message}"


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Northstar metadata-first knowledge corpus."
    )
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path("corpus/northstar"),
    )
    args = parser.parse_args()
    root = args.corpus_root
    if not root.is_dir():
        print(f"ERROR: corpus root does not exist: {root}", file=sys.stderr)
        return 1

    errors: list[ValidationError] = []
    paths = sorted(root.rglob("*.md"))
    ids: dict[str, Path] = {}
    bodies: dict[str, str] = {}

    legacy_indexes = sorted(root.rglob("_index.yaml"))
    for path in legacy_indexes:
        errors.append(
            ValidationError(
                path.relative_to(root).as_posix(),
                "legacy _index.yaml is not used by the metadata-first mechanism",
            )
        )

    if len(paths) != EXPECTED_DOCUMENT_COUNT:
        errors.append(
            ValidationError(
                str(root),
                f"expected {EXPECTED_DOCUMENT_COUNT} Markdown documents, found {len(paths)}",
            )
        )

    for path in paths:
        rel = path.relative_to(root)
        source = rel.as_posix()
        try:
            metadata, body = parse_frontmatter(path)
        except Exception as exc:
            errors.append(ValidationError(source, str(exc)))
            continue

        missing = REQUIRED_FRONTMATTER_FIELDS - metadata.keys()
        if missing:
            errors.append(
                ValidationError(source, "missing front matter fields: " + ", ".join(sorted(missing)))
            )
            continue

        document_id = metadata.get("id")
        title = metadata.get("title")
        description = metadata.get("description")
        version = metadata.get("version")
        if not isinstance(document_id, str) or not document_id.strip():
            errors.append(ValidationError(source, "id must be a non-empty string"))
            continue
        expected_id = ".".join(rel.with_suffix("").parts)
        if document_id != expected_id:
            errors.append(
                ValidationError(source, f"id {document_id!r} does not match path-derived id {expected_id!r}")
            )
        if document_id in ids:
            errors.append(ValidationError(source, f"duplicate id {document_id!r}"))
        ids[document_id] = path
        if not isinstance(title, str) or not title.strip():
            errors.append(ValidationError(source, "title must be a non-empty string"))
        if not isinstance(description, str) or not description.strip():
            errors.append(ValidationError(source, "description must be a non-empty string"))
        else:
            if len(description) > 1024:
                errors.append(ValidationError(source, "description exceeds 1024 characters"))
            if not re.search(r"\buse (?:for|when)\b", description, flags=re.IGNORECASE):
                errors.append(
                    ValidationError(
                        source,
                        "description must include an activation clause using 'Use for' or 'Use when'",
                    )
                )
        if not isinstance(version, int):
            errors.append(ValidationError(source, "version must be an integer"))
        if not body.strip():
            errors.append(ValidationError(source, "document body is empty"))
        bodies[document_id] = body

    # Detect document-ID-like references that point nowhere.
    id_pattern = re.compile(
        r"\b(?:operations|commercial|platform|governance)(?:\.[a-z0-9-]+){2,}\b"
    )
    reference_count = 0
    known_ids = set(ids)
    for document_id, body in bodies.items():
        for candidate in set(id_pattern.findall(body)):
            if candidate in known_ids:
                if candidate != document_id:
                    reference_count += 1
            else:
                errors.append(
                    ValidationError(
                        ids[document_id].relative_to(root).as_posix(),
                        f"references unknown document id {candidate!r}",
                    )
                )

    if errors:
        print(f"\nCorpus validation FAILED with {len(errors)} error(s):\n")
        for error in errors:
            print(f"  - {error}")
        print()
        return 1

    print("\nCorpus validation PASSED\n")
    print(f"  Documents:           {len(paths)}")
    print(f"  Metadata entries:    {len(ids)}")
    print(f"  Cross references:    {reference_count}")
    print("  Legacy indexes:      0")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
