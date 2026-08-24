#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from progressive_disclosure.knowledge import KnowledgeBase


def validate_dataset(path: Path, corpus_root: Path) -> list[str]:
    errors: list[str] = []
    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path}: cannot parse YAML: {exc}"]
    if not isinstance(data, dict):
        return [f"{path}: root must be a mapping"]
    profile = data.get("profile", "benchmark")
    if profile not in {"benchmark", "development"}:
        return [f"{path}: profile must be 'benchmark' or 'development'"]
    cases = data.get("cases")
    if not isinstance(cases, list):
        return [f"{path}: top-level cases must be a list"]

    knowledge = KnowledgeBase(corpus_root)
    all_docs = set(knowledge.document_ids)
    ids: set[str] = set()
    questions: set[str] = set()
    covered: set[str] = set()
    single = 0
    multi = 0

    for index, case in enumerate(cases):
        source = f"{path}:cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{source}: case must be a mapping")
            continue
        required_fields = {"id", "title", "question", "expected_contains", "required_documents", "tags"}
        missing = required_fields - case.keys()
        if missing:
            errors.append(f"{source}: missing fields {sorted(missing)}")
            continue
        case_id = case["id"]
        question = case["question"]
        expected = case["expected_contains"]
        required = case["required_documents"]
        tags = case["tags"]
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{source}: id must be non-empty string")
            continue
        if case_id in ids:
            errors.append(f"{source}: duplicate id {case_id}")
        ids.add(case_id)
        if not isinstance(question, str) or not question.strip():
            errors.append(f"{source}: question must be non-empty string")
            continue
        normalized_q = " ".join(question.split()).casefold()
        if normalized_q in questions:
            errors.append(f"{source}: duplicate question")
        questions.add(normalized_q)
        if not isinstance(expected, list) or not expected or not all(isinstance(x, str) and x for x in expected):
            errors.append(f"{source}: expected_contains must be non-empty string list")
        if not isinstance(required, list) or not required or not all(isinstance(x, str) for x in required):
            errors.append(f"{source}: required_documents must be non-empty string list")
            continue
        if not isinstance(tags, list) or not tags or not all(isinstance(x, str) and x for x in tags):
            errors.append(f"{source}: tags must be non-empty string list")
        unknown = set(required) - all_docs
        if unknown:
            errors.append(f"{source}: unknown required documents {sorted(unknown)}")
            continue
        covered.update(required)
        if len(required) == 1:
            single += 1
            if "single_doc" not in tags:
                errors.append(f"{source}: one-document case must have single_doc tag")
        else:
            multi += 1
            if "multi_doc" not in tags:
                errors.append(f"{source}: multi-document case must have multi_doc tag")

        evidence = "\n".join(knowledge.read(doc_id).content for doc_id in required).casefold()
        required_metadata = "\n".join(
            f"{knowledge.read(doc_id).title}\n{knowledge.read(doc_id).description}"
            for doc_id in required
        ).casefold()
        for value in expected:
            text = str(value).casefold()
            if text in normalized_q:
                errors.append(f"{source}: expected value leaks into question: {value!r}")
            metadata_pattern = re.compile(
                r"(?<![a-z0-9])" + re.escape(text) + r"(?![a-z0-9])"
            )
            if metadata_pattern.search(required_metadata):
                errors.append(f"{source}: expected value leaks into required-document metadata: {value!r}")
            if text not in evidence:
                errors.append(f"{source}: expected value not found in required evidence: {value!r}")

    if profile == "benchmark":
        if len(cases) < 60:
            errors.append(f"{path}: benchmark should contain at least 60 cases, found {len(cases)}")
        if single < 40:
            errors.append(f"{path}: benchmark should contain at least 40 single-document cases, found {single}")
        if multi < 20:
            errors.append(f"{path}: benchmark should contain at least 20 multi-document cases, found {multi}")
        missing_docs = all_docs - covered
        if missing_docs:
            errors.append(f"{path}: corpus documents without eval coverage: {sorted(missing_docs)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the held-out progressive-disclosure eval dataset.")
    parser.add_argument("--dataset", type=Path, default=Path("datasets/eval-v1.yaml"))
    parser.add_argument("--corpus-root", type=Path, default=Path("corpus/northstar"))
    args = parser.parse_args()
    errors = validate_dataset(args.dataset, args.corpus_root)
    if errors:
        print(f"Dataset validation FAILED with {len(errors)} error(s):\n")
        for error in errors:
            print(f"  - {error}")
        return 1
    data = yaml.safe_load(args.dataset.read_text(encoding="utf-8"))
    cases = data["cases"]
    knowledge = KnowledgeBase(args.corpus_root)
    print("Dataset validation PASSED\n")
    print(f"  Cases:              {len(cases)}")
    print(f"  Single-document:    {sum(len(c['required_documents']) == 1 for c in cases)}")
    print(f"  Multi-document:     {sum(len(c['required_documents']) > 1 for c in cases)}")
    print(f"  Corpus coverage:    {len({d for c in cases for d in c['required_documents']})}/{len(knowledge.document_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
