#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from _common import jsonable, serve


FRONTMATTER_ID = re.compile(r"(?m)^id:\s*[\"']?([^\n\"']+)[\"']?\s*$")


class HindsightWorker:
    def __init__(self) -> None:
        self.runtime_root: Path | None = None
        self.client: Any = None
        self.provider_version = self._version()

    @staticmethod
    def _version() -> str:
        for package in ("hindsight-all", "hindsight-all-slim", "hindsight-client"):
            try:
                return f"{package}=={importlib.metadata.version(package)}"
            except importlib.metadata.PackageNotFoundError:
                continue
        return "unknown"

    def _configure(self, runtime_root: str) -> None:
        root = Path(runtime_root).resolve()
        if self.runtime_root == root:
            return
        if self.client is not None:
            raise RuntimeError("cannot change Hindsight runtime root while client is active")
        self.runtime_root = root
        home = root / "home"
        cache = root / "cache"
        home.mkdir(parents=True, exist_ok=True)
        cache.mkdir(parents=True, exist_ok=True)
        # HindsightEmbedded persists its profile/pg0 state under HOME. Set this
        # before importing hindsight so all generated state remains disposable.
        os.environ["HOME"] = str(home)
        os.environ["XDG_CACHE_HOME"] = str(cache)
        os.environ.setdefault("HINDSIGHT_EMBED_PORT_HEALTH_GRACE_TIMEOUT", "60")

    def _ensure_client(self) -> Any:
        if self.client is not None:
            return self.client
        if self.runtime_root is None:
            raise RuntimeError("worker has not been initialized")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the Hindsight experiment")
        model = (
            os.getenv("MEMORY_EVAL_INGEST_MODEL")
            or os.getenv("MEMORY_EVAL_HINDSIGHT_LLM_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-5-nano"
        )
        from hindsight import HindsightEmbedded

        kwargs: dict[str, Any] = {
            "profile": "progressive-disclosure-memory-eval",
            "llm_provider": "openai",
            "llm_model": model,
            "llm_api_key": api_key,
            "idle_timeout": int(os.getenv("MEMORY_EVAL_HINDSIGHT_IDLE_TIMEOUT", "3600")),
        }
        base_url = os.getenv("MEMORY_EVAL_HINDSIGHT_LLM_BASE_URL")
        if base_url:
            kwargs["llm_base_url"] = base_url
        self.client = HindsightEmbedded(**kwargs)
        return self.client

    @staticmethod
    def _bank_id(corpus: str) -> str:
        return f"progressive-disclosure-{corpus}"

    @staticmethod
    def _document_id(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            frontmatter = text[3:end] if end >= 0 else text[:4000]
            match = FRONTMATTER_ID.search(frontmatter)
            if match:
                return match.group(1).strip()
        return path.stem

    @staticmethod
    def _hits(payload: Any) -> list[dict[str, Any]]:
        data = jsonable(payload)
        if not isinstance(data, dict):
            return [item if isinstance(item, dict) else {"value": item} for item in data] if isinstance(data, list) else []
        hits: list[dict[str, Any]] = []
        # Preserve Hindsight's ranked memory results first. Chunks/source facts
        # follow only as provenance-bearing fallback candidates.
        for key in ("results", "chunks", "source_facts"):
            value = data.get(key)
            if isinstance(value, list):
                for item in value:
                    normalized = item if isinstance(item, dict) else {"value": item}
                    normalized = dict(normalized)
                    normalized.setdefault("hindsight_section", key)
                    hits.append(normalized)
        return hits

    def hello(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        return {
            "backend": "hindsight",
            "provider_version": self.provider_version,
            "python": sys.version.split()[0],
        }

    def ingest(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        client = self._ensure_client()
        corpus = str(request["corpus"])
        memory_root = Path(request["memory_root"]).resolve()
        bank_id = self._bank_id(corpus)
        paths = sorted(memory_root.rglob("*.md"))
        started = time.perf_counter()

        # Configure the bank for a static technical corpus. We retain normal
        # extraction/consolidation behavior so this measures Hindsight as a memory
        # system, not merely its underlying vector store.
        try:
            client.create_bank(
                bank_id,
                retain_mission=(
                    "Extract exact technical facts, identifiers, numeric values, constraints, "
                    "exceptions, decisions, and relationships from the supplied Markdown. "
                    "Preserve qualifiers and source-specific details needed to answer questions."
                ),
                enable_text_search=True,
                enable_temporal_retrieval=True,
                enable_graph_retrieval=True,
                enable_reranking=True,
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).casefold()
            if not any(token in message for token in ("already", "exists", "409", "conflict")):
                raise

        items: list[dict[str, Any]] = []
        for path in paths:
            doc_id = self._document_id(path)
            relative = path.relative_to(memory_root).as_posix()
            items.append(
                {
                    "content": path.read_text(encoding="utf-8"),
                    "context": (
                        f"Canonical Markdown knowledge document {doc_id} from corpus {corpus}; "
                        f"source path {relative}."
                    ),
                    "document_id": doc_id,
                    "metadata": {"source_path": relative, "corpus": corpus, "document_id": doc_id},
                    "tags": [f"corpus:{corpus}", "source:markdown"],
                    "update_mode": "replace",
                }
            )

        batch_size = max(1, int(os.getenv("MEMORY_EVAL_HINDSIGHT_BATCH_SIZE", "10")))
        retained = 0
        total_batches = (len(items) + batch_size - 1) // batch_size
        for batch_index, start in enumerate(range(0, len(items), batch_size), start=1):
            batch = items[start : start + batch_size]
            first = start + 1
            last = start + len(batch)
            print(
                f"Hindsight retain {corpus} batch {batch_index}/{total_batches} "
                f"documents {first}-{last}/{len(items)}",
                file=sys.stderr,
                flush=True,
            )
            client.retain_batch(bank_id=bank_id, items=batch)
            retained += len(batch)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "backend": "hindsight",
            "provider_version": self.provider_version,
            "documents": retained,
            "elapsed_ms": elapsed_ms,
            "bank_id": bank_id,
            "metadata": {
                "recall_budget": os.getenv("MEMORY_EVAL_HINDSIGHT_RECALL_BUDGET", "mid"),
                "retain_mode": "provider_default_fact_extraction_plus_consolidation",
            },
        }

    def query(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        client = self._ensure_client()
        corpus = str(request["corpus"])
        query = str(request["query"])
        limit = int(request["limit"])
        bank_id = self._bank_id(corpus)
        max_tokens = int(os.getenv("MEMORY_EVAL_HINDSIGHT_RECALL_MAX_TOKENS", "8192"))
        budget = os.getenv("MEMORY_EVAL_HINDSIGHT_RECALL_BUDGET", "mid")
        started = time.perf_counter()
        result = client.recall(
            bank_id=bank_id,
            query=query,
            max_tokens=max_tokens,
            budget=budget,
            include_chunks=True,
            max_chunk_tokens=max_tokens,
            include_source_facts=True,
            max_source_facts_tokens=max_tokens,
            tags=[f"corpus:{corpus}"],
            tags_match="all_strict",
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        hits = self._hits(result)[:limit]
        return {
            "backend": "hindsight",
            "provider_version": self.provider_version,
            "requested_limit": limit,
            "elapsed_ms": elapsed_ms,
            "retrieval_llm_calls": 0,
            "hits": hits,
            "metadata": {
                "bank_id": bank_id,
                "budget": budget,
                "max_tokens": max_tokens,
            },
        }

    def close(self) -> dict[str, Any]:
        if self.client is not None:
            close = getattr(self.client, "close", None)
            if callable(close):
                try:
                    close(stop_daemon=True)
                except TypeError:
                    close()
                except Exception:
                    pass
            self.client = None
        return {"closed": True}

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        operation = request.get("op")
        if operation == "hello":
            return self.hello(request)
        if operation == "ingest":
            return self.ingest(request)
        if operation == "query":
            return self.query(request)
        if operation == "close":
            return self.close()
        raise ValueError(f"unsupported operation: {operation!r}")


if __name__ == "__main__":
    worker = HindsightWorker()
    try:
        serve(worker.handle)
    finally:
        worker.close()
