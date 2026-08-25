#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from progressive_disclosure.corpora import CORPORA, corpus_name_from_dataset, get_corpus_spec
from progressive_disclosure.knowledge import KnowledgeBase


def _load(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"{path}: cannot parse YAML: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{path}: root must be a mapping"]
    return data, []


def resolve_corpus_root(data: dict[str, Any], corpus_root: Path | None = None, corpus_name: str | None = None) -> tuple[str, Path]:
    if corpus_name:
        spec = get_corpus_spec(corpus_name)
        return spec.name, corpus_root or spec.root
    inferred = corpus_name_from_dataset(data)
    spec = get_corpus_spec(inferred)
    return spec.name, corpus_root or spec.root


def validate_dataset(path: Path, corpus_root: Path | None = None, corpus_name: str | None = None) -> list[str]:
    data, errors = _load(path)
    if data is None:
        return errors

    name = data.get("name")
    version = data.get("version")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{path}: name must be a non-empty string")
    if not isinstance(version, int):
        errors.append(f"{path}: version must be an integer")

    profile = data.get("profile", "benchmark")
    if profile not in {"benchmark", "development"}:
        errors.append(f"{path}: profile must be 'benchmark' or 'development'")
    cases = data.get("cases")
    if not isinstance(cases, list):
        return errors + [f"{path}: top-level cases must be a list"]

    try:
        resolved_name, root = resolve_corpus_root(data, corpus_root, corpus_name)
        knowledge = KnowledgeBase(root)
    except Exception as exc:
        return errors + [f"{path}: cannot load corpus: {exc}"]

    all_docs = set(knowledge.document_ids)
    ids: set[str] = set()
    questions: set[str] = set()
    covered: set[str] = set()
    single = 0
    multi = 0
    strict_multi = bool(data.get("require_indispensable_expected_contribution", False))

    activation_metadata = "\n".join(
        f"{item.title}\n{item.description}" for item in knowledge.catalog()
    ).casefold()
    global_metadata_leakage = bool(data.get("check_global_metadata_leakage", False))

    for index, case in enumerate(cases):
        source = f"{path}:cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{source}: case must be a mapping")
            continue
        required_fields = {"id", "question", "expected_contains", "required_documents", "tags"}
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
        if not isinstance(required, list) or not required or not all(isinstance(x, str) and x for x in required):
            errors.append(f"{source}: required_documents must be non-empty string list")
            continue
        if len(required) > 4:
            errors.append(f"{source}: required_documents exceeds runtime maximum of 4")
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

        bodies = {doc_id: knowledge.read(doc_id).content for doc_id in required}
        evidence = "\n".join(bodies.values()).casefold()
        required_evidence = case.get("required_evidence")
        if required_evidence is not None:
            if not isinstance(required_evidence, dict) or not required_evidence:
                errors.append(f"{source}: required_evidence must be a non-empty mapping when present")
                required_evidence = {}
            elif set(required_evidence) != set(required):
                errors.append(
                    f"{source}: required_evidence keys must exactly match required_documents"
                )
            for doc_id, values in required_evidence.items() if isinstance(required_evidence, dict) else []:
                if doc_id not in bodies:
                    continue
                if not isinstance(values, list) or not values or not all(isinstance(x, str) and x for x in values):
                    errors.append(f"{source}: required_evidence[{doc_id!r}] must be a non-empty string list")
                    continue
                body_folded = bodies[doc_id].casefold()
                for value in values:
                    if value.casefold() not in body_folded:
                        errors.append(
                            f"{source}: required evidence value not found in {doc_id}: {value!r}"
                        )

        for value in expected if isinstance(expected, list) else []:
            text = value.casefold()
            if text in normalized_q:
                errors.append(f"{source}: expected value leaks into question: {value!r}")
            pattern = re.compile(r"(?<![a-z0-9])" + re.escape(text) + r"(?![a-z0-9])")
            if global_metadata_leakage:
                metadata_to_check = activation_metadata
            else:
                metadata_to_check = "\n".join(
                    f"{knowledge.read(doc_id).title}\n{knowledge.read(doc_id).description}"
                    for doc_id in required
                ).casefold()
            if pattern.search(metadata_to_check):
                errors.append(f"{source}: expected value leaks into activation metadata: {value!r}")
            if text not in evidence:
                errors.append(f"{source}: expected value not found in required evidence: {value!r}")

        if strict_multi and len(required) > 1:
            if isinstance(required_evidence, dict) and required_evidence:
                for doc_id in required:
                    values = required_evidence.get(doc_id, [])
                    contributes = any(
                        isinstance(value, str)
                        and value.casefold() in bodies[doc_id].casefold()
                        and not any(
                            value.casefold() in bodies[other].casefold()
                            for other in required
                            if other != doc_id
                        )
                        for value in values
                    )
                    if not contributes:
                        errors.append(
                            f"{source}: redundant required document by required_evidence contribution check: {doc_id}"
                        )
            elif isinstance(expected, list):
                for doc_id in required:
                    contributes = any(
                        value.casefold() in bodies[doc_id].casefold()
                        and not any(
                            value.casefold() in bodies[other].casefold()
                            for other in required
                            if other != doc_id
                        )
                        for value in expected
                    )
                    if not contributes:
                        errors.append(
                            f"{source}: redundant required document by expected-value contribution check: {doc_id}"
                        )

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

    if data.get("corpus") != resolved_name:
        errors.append(f"{path}: dataset corpus field must be {resolved_name!r}")
    return errors


def _print_one(path: Path, corpus_root: Path | None = None, corpus_name: str | None = None) -> bool:
    errors = validate_dataset(path, corpus_root, corpus_name)
    if errors:
        print(f"Dataset validation FAILED [{path}] with {len(errors)} error(s):\n")
        for error in errors:
            print(f"  - {error}")
        return False
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    resolved_name, root = resolve_corpus_root(data, corpus_root, corpus_name)
    knowledge = KnowledgeBase(root)
    cases = data["cases"]
    print(f"Dataset validation PASSED [{resolved_name}]\n")
    print(f"  Dataset:            {data['name']} v{data['version']}")
    print(f"  Cases:              {len(cases)}")
    print(f"  Single-document:    {sum(len(c['required_documents']) == 1 for c in cases)}")
    print(f"  Multi-document:     {sum(len(c['required_documents']) > 1 for c in cases)}")
    print(f"  Corpus coverage:    {len({d for c in cases for d in c['required_documents']})}/{len(knowledge.document_ids)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate progressive-disclosure evaluation datasets.")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--corpus", choices=tuple(CORPORA))
    parser.add_argument("--corpus-root", type=Path)
    parser.add_argument("--all", action="store_true", help="Validate each registered corpus's default benchmark dataset")
    args = parser.parse_args()
    if args.all and (args.dataset or args.corpus or args.corpus_root):
        parser.error("--all cannot be combined with --dataset, --corpus, or --corpus-root")

    if args.all:
        ok = True
        for spec in CORPORA.values():
            ok = _print_one(spec.default_dataset, corpus_name=spec.name) and ok
        return 0 if ok else 1

    if args.dataset is not None:
        path = args.dataset
    elif args.corpus:
        path = get_corpus_spec(args.corpus).default_dataset
    else:
        path = get_corpus_spec("northstar").default_dataset
    return 0 if _print_one(path, args.corpus_root, args.corpus) else 1


if __name__ == "__main__":
    raise SystemExit(main())
