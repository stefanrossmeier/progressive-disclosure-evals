#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from progressive_disclosure.corpora import corpus_names
from qwen_rag_pipeline.index import DEFAULT_INDEX_ROOT, DEFAULT_QUERY_INSTRUCTION, build_index
from qwen_rag_pipeline.model_assets import DEFAULT_MODEL_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local Qwen hierarchical-RAG indexes.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--corpus", choices=corpus_names())
    group.add_argument("--all", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    parser.add_argument("--query-instruction", default=DEFAULT_QUERY_INSTRUCTION)
    parser.add_argument("--chunk-words", type=int, default=320)
    parser.add_argument("--overlap-words", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    args = parser.parse_args()

    names = corpus_names() if args.all else (args.corpus,)
    for name in names:
        target = build_index(
            name,
            output_dir=args.output_root / name,
            model_root=args.model_root,
            query_instruction=args.query_instruction,
            chunk_words=args.chunk_words,
            overlap_words=args.overlap_words,
            batch_size=args.batch_size,
            device=args.device,
        )
        print(f"built {name} Qwen RAG index: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
