#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from progressive_disclosure.corpora import corpus_names
from rag_baseline.index import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_INDEX_ROOT,
    DEFAULT_QUERY_PREFIX,
    build_index,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build fully local dense RAG indexes for the benchmark corpora.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--corpus", choices=corpus_names())
    group.add_argument("--all", action="store_true", help="Build an index for every configured corpus")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_INDEX_ROOT)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--query-prefix", default=DEFAULT_QUERY_PREFIX)
    parser.add_argument("--chunk-words", type=int, default=320)
    parser.add_argument("--overlap-words", type=int, default=64)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", help="sentence-transformers device, e.g. cpu, mps, cuda")
    parser.add_argument("--offline", action="store_true", help="Require the embedding model to already exist in the local cache")
    args = parser.parse_args()

    names = corpus_names() if args.all else (args.corpus,)
    for name in names:
        target = build_index(
            name,
            output_dir=args.output_root / name,
            embedding_model=args.embedding_model,
            query_prefix=args.query_prefix,
            chunk_words=args.chunk_words,
            overlap_words=args.overlap_words,
            batch_size=args.batch_size,
            device=args.device,
            offline=args.offline,
        )
        print(f"built {name} RAG index: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
