from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


def discover_trial_files(paths: Iterable[Path | str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            found.append(path)
        elif path.is_dir():
            direct = path / "trials.jsonl"
            if direct.is_file():
                found.append(direct)
            else:
                found.extend(sorted(path.rglob("trials.jsonl")))
        else:
            raise FileNotFoundError(path)
    unique = []
    seen = set()
    for path in found:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    if not unique:
        raise ValueError("no trials.jsonl files found")
    return unique


def load_records(paths: Iterable[Path | str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in discover_trial_files(paths):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            record["_source_file"] = str(path)
            records.append(record)
    return records


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _std(values: list[float]) -> float | None:
    return statistics.pstdev(values) if len(values) > 1 else (0.0 if values else None)


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _rate(flags: list[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [
        r
        for r in records
        if r.get("status") == "completed" and isinstance(r.get("result"), dict)
    ]
    errors = [r for r in records if r.get("status") == "error"]

    overall_success = [bool(r["result"].get("overall_success")) for r in completed]
    discovery_success = [
        bool(r["result"].get("discovery", {}).get("complete_discovery"))
        for r in completed
    ]
    answer_success = [bool(r["result"].get("answer_contains_expected")) for r in completed]
    attribution_success = [bool(r["result"].get("required_sources_cited")) for r in completed]
    first_read_hits = [
        r["result"].get("discovery", {}).get("wrong_documents_before_first_gold") == 0
        for r in completed
        if r.get("required_documents")
    ]
    stopping_flags = [
        r["result"].get("discovery", {}).get("reads_after_complete_discovery") == 0
        for r in completed
        if r["result"].get("discovery", {}).get("complete_discovery")
    ]

    document_reads = [float(r["result"].get("document_reads", 0)) for r in completed]
    model_turns = [float(r["result"].get("model_turns", 0)) for r in completed]
    input_tokens = [float(r["result"].get("input_tokens", 0)) for r in completed]
    output_tokens = [float(r["result"].get("output_tokens", 0)) for r in completed]
    precisions = [
        float(r["result"].get("discovery", {}).get("document_precision", 0.0))
        for r in completed
    ]
    fractions = [
        float(r["result"].get("context", {}).get("knowledge_content_fraction_loaded", 0.0))
        for r in completed
    ]

    successful_trials = sum(overall_success)
    trial_count = len(records)
    return {
        "trials": trial_count,
        "completed": len(completed),
        "errors": len(errors),
        "completion_rate": len(completed) / trial_count if trial_count else None,
        # Success among model trials that actually completed. Kept for compatibility.
        "overall_success_rate": _rate(overall_success),
        # End-to-end rate counts API/runtime errors as unsuccessful benchmark trials.
        "end_to_end_success_rate": successful_trials / trial_count if trial_count else None,
        "discovery_success_rate": _rate(discovery_success),
        "answer_accuracy": _rate(answer_success),
        "attribution_rate": _rate(attribution_success),
        "first_read_hit_rate": _rate(first_read_hits),
        "evidence_stopping_rate": _rate(stopping_flags),
        "mean_document_precision": _mean(precisions),
        "mean_document_reads": _mean(document_reads),
        "std_document_reads": _std(document_reads),
        "median_document_reads": _median(document_reads),
        "p95_document_reads": _p95(document_reads),
        "mean_model_calls": _mean(model_turns),
        "std_model_calls": _std(model_turns),
        "mean_input_tokens": _mean(input_tokens),
        "std_input_tokens": _std(input_tokens),
        "mean_output_tokens": _mean(output_tokens),
        "std_output_tokens": _std(output_tokens),
        "mean_knowledge_fraction_loaded": _mean(fractions),
    }


def _group(
    records: list[dict[str, Any]],
    key_fn: Callable[[dict[str, Any]], Iterable[str]],
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for key in key_fn(record):
            groups[key].append(record)
    return {key: summarize_records(value) for key, value in sorted(groups.items())}


def _prompt_label(record: dict[str, Any]) -> str:
    label = f"{record.get('prompt_id')}@v{record.get('prompt_version')}"
    digest = record.get("prompt_sha256")
    if isinstance(digest, str) and digest:
        label += f"#{digest[:8]}"
    return label


def _provenance(records: list[dict[str, Any]]) -> dict[str, Any]:
    def values(key: str) -> list[str]:
        return sorted({str(r[key]) for r in records if r.get(key)})

    return {
        "dataset_sha256": values("dataset_sha256"),
        "corpus_sha256": values("corpus_sha256"),
        "prompt_sha256": values("prompt_sha256"),
        "records_without_dataset_hash": sum(not bool(r.get("dataset_sha256")) for r in records),
        "records_without_corpus_hash": sum(not bool(r.get("corpus_sha256")) for r in records),
        "records_without_prompt_hash": sum(not bool(r.get("prompt_sha256")) for r in records),
    }


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "overall": summarize_records(records),
        "provenance": _provenance(records),
        "errors_by_type": dict(
            sorted(Counter(str(r.get("error_type") or "unknown") for r in records if r.get("status") == "error").items())
        ),
        "by_corpus": _group(records, lambda r: [str(r.get("corpus_name") or "unknown")]),
        "by_prompt_model": _group(
            records,
            lambda r: [f"{r.get('model')} :: {_prompt_label(r)}"],
        ),
        "by_prompt": _group(records, lambda r: [_prompt_label(r)]),
        "by_model": _group(records, lambda r: [str(r.get("model"))]),
        "by_repeat": _group(records, lambda r: [str(r.get("repeat_index"))]),
        "by_case": _group(records, lambda r: [str(r.get("case_id"))]),
        "by_tag": _group(records, lambda r: [str(tag) for tag in r.get("tags", [])]),
        "by_document": _group(
            records,
            lambda r: [str(doc) for doc in r.get("required_documents", [])],
        ),
    }


def _md_cell(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")


def _table(rows: list[list[Any]], headers: list[str]) -> str:
    lines = [
        "| " + " | ".join(_md_cell(x) for x in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(_md_cell(x) for x in row) + " |" for row in rows)
    return "\n".join(lines)


def _quality_row(name: str, summary: dict[str, Any]) -> list[str]:
    return [
        name,
        str(summary["trials"]),
        str(summary["completed"]),
        str(summary["errors"]),
        _pct(summary["completion_rate"]),
        _pct(summary["end_to_end_success_rate"]),
        _pct(summary["overall_success_rate"]),
        _pct(summary["discovery_success_rate"]),
        _pct(summary["answer_accuracy"]),
        _pct(summary["attribution_rate"]),
        _pct(summary["first_read_hit_rate"]),
        _pct(summary["evidence_stopping_rate"]),
    ]


def _efficiency_row(name: str, summary: dict[str, Any]) -> list[str]:
    docs = (
        f"{summary['mean_document_reads']:.2f}±{summary['std_document_reads']:.2f}"
        if summary["mean_document_reads"] is not None
        else "—"
    )
    calls = (
        f"{summary['mean_model_calls']:.2f}±{summary['std_model_calls']:.2f}"
        if summary["mean_model_calls"] is not None
        else "—"
    )
    input_tokens = (
        f"{summary['mean_input_tokens']:.0f}±{summary['std_input_tokens']:.0f}"
        if summary["mean_input_tokens"] is not None
        else "—"
    )
    output_tokens = (
        f"{summary['mean_output_tokens']:.0f}±{summary['std_output_tokens']:.0f}"
        if summary["mean_output_tokens"] is not None
        else "—"
    )
    return [
        name,
        _pct(summary["mean_document_precision"]),
        docs,
        f"{summary['median_document_reads']:.2f}" if summary["median_document_reads"] is not None else "—",
        f"{summary['p95_document_reads']:.2f}" if summary["p95_document_reads"] is not None else "—",
        calls,
        input_tokens,
        output_tokens,
        _pct(summary["mean_knowledge_fraction_loaded"]),
    ]


QUALITY_HEADERS = [
    "Group",
    "Trials",
    "Completed",
    "Errors",
    "Completion",
    "E2E success",
    "Task success",
    "Discovery",
    "Answer",
    "Attribution",
    "First-read hit",
    "Stop after evidence",
]

EFFICIENCY_HEADERS = [
    "Group",
    "Doc precision",
    "Docs μ±σ",
    "Docs median",
    "Docs p95",
    "Calls μ±σ",
    "Input tok μ±σ",
    "Output tok μ±σ",
    "Knowledge loaded",
]


def _append_group_section(
    lines: list[str],
    title: str,
    groups: dict[str, dict[str, Any]],
    *,
    include_efficiency: bool = True,
) -> None:
    lines.extend(["", f"## {title}", ""])
    lines.append(_table([_quality_row(k, v) for k, v in groups.items()], QUALITY_HEADERS))
    if include_efficiency:
        lines.extend(["", "### Efficiency", ""])
        lines.append(_table([_efficiency_row(k, v) for k, v in groups.items()], EFFICIENCY_HEADERS))


def _difficulty_key(item: tuple[str, dict[str, Any]]) -> tuple[Any, ...]:
    key, value = item

    def low(metric: str) -> float:
        result = value.get(metric)
        return float(result) if result is not None else -1.0

    reads = value.get("mean_document_reads")
    return (
        low("completion_rate"),
        low("end_to_end_success_rate"),
        low("discovery_success_rate"),
        low("answer_accuracy"),
        low("attribution_rate"),
        low("first_read_hit_rate"),
        low("evidence_stopping_rate"),
        low("mean_document_precision"),
        -(float(reads) if reads is not None else 0.0),
        key,
    )


def _is_variable(value: dict[str, Any]) -> bool:
    if value["completed"] < 2:
        return False
    for metric in (
        "overall_success_rate",
        "discovery_success_rate",
        "answer_accuracy",
        "attribution_rate",
        "first_read_hit_rate",
        "evidence_stopping_rate",
    ):
        rate = value.get(metric)
        if rate is not None and 0.0 < rate < 1.0:
            return True
    return bool((value.get("std_document_reads") or 0.0) > 0.0)


def render_markdown(summary: dict[str, Any]) -> str:
    lines = ["# Progressive Disclosure Eval Report", "", "## Overall", ""]
    lines.append(_table([_quality_row("all", summary["overall"])], QUALITY_HEADERS))
    lines.extend(["", "### Efficiency", ""])
    lines.append(_table([_efficiency_row("all", summary["overall"])], EFFICIENCY_HEADERS))

    provenance = summary.get("provenance", {})
    lines.extend(["", "## Reproducibility", ""])
    dataset_hashes = provenance.get("dataset_sha256", [])
    corpus_hashes = provenance.get("corpus_sha256", [])
    prompt_hashes = provenance.get("prompt_sha256", [])
    lines.append(f"- Dataset fingerprints: {', '.join(dataset_hashes) if dataset_hashes else 'unavailable'}")
    lines.append(f"- Corpus fingerprints: {', '.join(corpus_hashes) if corpus_hashes else 'unavailable'}")
    lines.append(f"- Prompt fingerprints: {', '.join(prompt_hashes) if prompt_hashes else 'unavailable'}")
    if len(dataset_hashes) > 1:
        lines.append("- **Warning:** results contain multiple dataset versions/content fingerprints.")
    if len(corpus_hashes) > 1:
        lines.append("- **Warning:** results contain multiple corpus content fingerprints.")
    missing = max(
        provenance.get("records_without_dataset_hash", 0),
        provenance.get("records_without_corpus_hash", 0),
        provenance.get("records_without_prompt_hash", 0),
    )
    if missing:
        lines.append(
            f"- {missing} record(s) predate artifact fingerprinting; provenance is incomplete for those trials."
        )

    _append_group_section(lines, "By corpus", summary["by_corpus"])
    _append_group_section(lines, "Prompt × model comparison", summary["by_prompt_model"])
    _append_group_section(lines, "By prompt", summary["by_prompt"], include_efficiency=False)
    _append_group_section(lines, "By model", summary["by_model"], include_efficiency=False)
    _append_group_section(lines, "By repeat", summary["by_repeat"], include_efficiency=False)
    _append_group_section(lines, "By tag", summary["by_tag"], include_efficiency=False)

    hardest = sorted(summary["by_case"].items(), key=_difficulty_key)[:15]
    lines.extend(["", "## Hardest cases", ""])
    lines.append(_table([_quality_row(k, v) for k, v in hardest], QUALITY_HEADERS))
    lines.extend(["", "### Hardest-case efficiency", ""])
    lines.append(_table([_efficiency_row(k, v) for k, v in hardest], EFFICIENCY_HEADERS))

    variable = [(key, value) for key, value in summary["by_case"].items() if _is_variable(value)]
    variable.sort(
        key=lambda kv: (
            -(kv[1].get("std_document_reads") or 0.0),
            kv[1].get("overall_success_rate") if kv[1].get("overall_success_rate") is not None else -1,
            kv[0],
        )
    )
    lines.extend(["", "## Run-to-run variable cases", ""])
    if variable:
        lines.append(_table([_quality_row(k, v) for k, v in variable[:15]], QUALITY_HEADERS))
        lines.extend(["", "### Variable-case efficiency", ""])
        lines.append(_table([_efficiency_row(k, v) for k, v in variable[:15]], EFFICIENCY_HEADERS))
    else:
        lines.append("No case showed mixed quality/stopping outcomes or variable document-read counts across repeated runs.")

    lines.extend(["", "## Per-document discovery coverage", ""])
    doc_headers = [
        "Required document",
        "Trials",
        "Discovery",
        "First-read hit",
        "Stop after evidence",
        "Doc precision",
        "Mean docs",
    ]
    doc_rows = []
    for key, value in summary["by_document"].items():
        doc_rows.append(
            [
                key,
                str(value["trials"]),
                _pct(value["discovery_success_rate"]),
                _pct(value["first_read_hit_rate"]),
                _pct(value["evidence_stopping_rate"]),
                _pct(value["mean_document_precision"]),
                f"{value['mean_document_reads']:.2f}" if value["mean_document_reads"] is not None else "—",
            ]
        )
    lines.append(_table(doc_rows, doc_headers))

    lines.extend(["", "## Execution errors", ""])
    errors_by_type = summary.get("errors_by_type", {})
    if errors_by_type:
        lines.append(_table([[name, count] for name, count in errors_by_type.items()], ["Error type", "Count"]))
    else:
        lines.append("No execution errors were recorded.")

    lines.append("")
    return "\n".join(lines)


def write_aggregate(records: list[dict[str, Any]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = aggregate(records)
    summary_path = output_dir / "summary.json"
    report_path = output_dir / "report.md"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_markdown(summary), encoding="utf-8")
    return summary_path, report_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate progressive-disclosure benchmark JSONL results."
    )
    parser.add_argument("paths", nargs="+", help="trials.jsonl files or result directories")
    parser.add_argument(
        "--output", type=Path, help="Output directory (default: first input directory)"
    )
    args = parser.parse_args()
    records = load_records(args.paths)
    if args.output:
        output = args.output
    else:
        first = Path(args.paths[0])
        output = first if first.is_dir() else first.parent
    summary_path, report_path = write_aggregate(records, output)
    print(summary_path)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
