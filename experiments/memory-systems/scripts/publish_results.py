#!/usr/bin/env python3
"""Create a commit-safe snapshot from a raw memory-system benchmark run.

Raw run directories intentionally keep provider traces and runtime logs and are
ignored by Git. This script preserves the reproducibility-critical aggregates,
manifests, and a normalized per-case record while omitting bulky raw provider
hits and machine-specific runtime state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

BACKENDS = ("basic-memory", "openviking", "hindsight")
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLISHED_ROOT = EXPERIMENT_ROOT / "results" / "published"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compact_trial(record: dict[str, Any]) -> dict[str, Any]:
    result = record["result"]
    discovery = result["discovery"]
    retrieval = result["retrieval"]
    context = result["context"]
    return {
        "schema_version": 1,
        "backend": retrieval.get("provider"),
        "case_id": record["case_id"],
        "case_title": record.get("case_title"),
        "corpus_name": record["corpus_name"],
        "tags": record.get("tags", []),
        "question": record["question"],
        "required_documents": record.get("required_documents", []),
        "expected_contains": record.get("expected_contains", []),
        "answer": result.get("answer"),
        "cited_sources": result.get("cited_sources", []),
        "opened_documents": result.get("opened_documents", []),
        "answer_correct": bool(result.get("answer_contains_expected")),
        "complete_discovery": bool(discovery.get("complete_discovery")),
        "answer_and_discovery": bool(result.get("answer_and_discovery")),
        "attribution_complete": bool(result.get("required_sources_cited")),
        "failure_classification": result.get("failure_classification"),
        "required_document_recall": discovery.get("required_document_recall"),
        "document_precision": discovery.get("document_precision"),
        "wrong_documents_before_first_gold": discovery.get("wrong_documents_before_first_gold"),
        "reads_to_complete_discovery": discovery.get("reads_to_complete_discovery"),
        "retrieval_ms": retrieval.get("retrieval_ms"),
        "provider_version": retrieval.get("provider_version"),
        "provider_hit_count": retrieval.get("provider_hit_count"),
        "unresolved_provider_hits": retrieval.get("unresolved_provider_hits"),
        "input_tokens": result.get("input_tokens"),
        "output_tokens": result.get("output_tokens"),
        "knowledge_content_fraction_loaded": context.get("knowledge_content_fraction_loaded"),
        "corpus_sha256": record.get("corpus_sha256"),
        "dataset_sha256": record.get("dataset_sha256"),
        "prompt_sha256": record.get("prompt_sha256"),
    }


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def copy_required(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def publish(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite published snapshot: {destination}")

    for name in ("comparison.json", "comparison.md"):
        if not (source / name).is_file():
            raise FileNotFoundError(source / name)
    for backend in BACKENDS:
        for name in ("manifest.json", "summary.json", "report.md", "trials.jsonl"):
            if not (source / backend / name).is_file():
                raise FileNotFoundError(source / backend / name)

    destination.mkdir(parents=True)
    copy_required(source / "comparison.json", destination / "comparison.json")
    copy_required(source / "comparison.md", destination / "comparison.md")

    raw_artifacts: dict[str, Any] = {
        "schema_version": 1,
        "source_run_directory": source.name,
        "note": (
            "Raw trials.jsonl files are not committed because provider hits repeat large source payloads. "
            "cases.jsonl preserves normalized per-case outcomes and retrieval mappings; SHA-256 values below "
            "identify the exact raw trial files from which the snapshot was derived."
        ),
        "backends": {},
    }

    for backend in BACKENDS:
        src_backend = source / backend
        dst_backend = destination / backend
        dst_backend.mkdir()
        for name in ("manifest.json", "summary.json", "report.md"):
            copy_required(src_backend / name, dst_backend / name)

        raw_trials = src_backend / "trials.jsonl"
        compact_path = dst_backend / "cases.jsonl"
        count = 0
        with compact_path.open("w", encoding="utf-8") as handle:
            for record in iter_jsonl(raw_trials):
                handle.write(json.dumps(compact_trial(record), ensure_ascii=False, sort_keys=True) + "\n")
                count += 1
        raw_artifacts["backends"][backend] = {
            "raw_trials_file": "trials.jsonl",
            "raw_trials_bytes": raw_trials.stat().st_size,
            "raw_trials_sha256": sha256_file(raw_trials),
            "published_cases": count,
            "published_cases_sha256": sha256_file(compact_path),
        }

    (destination / "raw-artifacts.json").write_text(
        json.dumps(raw_artifacts, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (destination / "README.md").write_text(
        "# Published memory-system benchmark snapshot\n\n"
        f"Source raw run: `{source.name}`.\n\n"
        "This directory is the commit-safe form of the raw benchmark run. It keeps the generated "
        "comparison, each backend manifest/summary/report, and a normalized `cases.jsonl` with one "
        "record per benchmark question. Bulky provider-internal raw retrieval hits and runtime logs are "
        "intentionally excluded. Their exact raw `trials.jsonl` SHA-256 values are recorded in "
        "`raw-artifacts.json`.\n\n"
        "See `../../../SETUP.md` for reproduction and "
        "`../../../../../docs/memory-system-evaluation-2026-09-22.md` for interpretation.\n",
        encoding="utf-8",
    )

    checksums: list[str] = []
    for path in sorted(p for p in destination.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        checksums.append(f"{sha256_file(path)}  {path.relative_to(destination).as_posix()}")
    (destination / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="raw timestamped result directory")
    parser.add_argument(
        "--name",
        help="published snapshot directory name; defaults to the source directory name",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=DEFAULT_PUBLISHED_ROOT,
        help=f"default: {DEFAULT_PUBLISHED_ROOT}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    name = args.name or args.source.name
    destination = args.destination_root / name
    publish(args.source, destination)
    print(f"published: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
