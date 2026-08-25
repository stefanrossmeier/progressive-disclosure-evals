#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from evals.aggregate import load_records, summarize_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare progressive-disclosure and RAG result directories.")
    parser.add_argument(
        "--result",
        action="append",
        required=True,
        metavar="LABEL=PATH",
        help="Repeat for each result set, e.g. progressive=results/...",
    )
    parser.add_argument("--output", type=Path, default=Path("retrieval-comparison.md"))
    args = parser.parse_args()

    rows: list[tuple[str, dict]] = []
    for raw in args.result:
        if "=" not in raw:
            parser.error("--result must be LABEL=PATH")
        label, raw_path = raw.split("=", 1)
        rows.append((label, summarize_records(load_records([Path(raw_path)]))))

    lines = [
        "# Retrieval architecture comparison",
        "",
        "| System | Trials | E2E | Answer | Discovery | Attribution | Doc precision | Mean docs | p95 docs | Mean calls | Knowledge loaded |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, summary in rows:
        pct = lambda key: "—" if summary[key] is None else f"{100 * summary[key]:.1f}%"
        num = lambda key: "—" if summary[key] is None else f"{summary[key]:.2f}"
        lines.append(
            "| " + " | ".join(
                [
                    label,
                    str(summary["trials"]),
                    pct("end_to_end_success_rate"),
                    pct("answer_accuracy"),
                    pct("discovery_success_rate"),
                    pct("attribution_rate"),
                    pct("mean_document_precision"),
                    num("mean_document_reads"),
                    num("p95_document_reads"),
                    num("mean_model_calls"),
                    pct("mean_knowledge_fraction_loaded"),
                ]
            ) + " |"
        )
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
