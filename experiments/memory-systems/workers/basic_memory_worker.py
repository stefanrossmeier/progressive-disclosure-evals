#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from _common import environment_executable, serve


class BasicMemoryWorker:
    def __init__(self) -> None:
        self.runtime_root: Path | None = None
        self.env: dict[str, str] | None = None
        self.provider_version = importlib.metadata.version("basic-memory")

    def _configure(self, runtime_root: str) -> None:
        root = Path(runtime_root).resolve()
        if self.runtime_root == root and self.env is not None:
            return
        self.runtime_root = root
        home = root / "home"
        xdg = root / "xdg"
        for path in (home, xdg / "config", xdg / "data", xdg / "cache"):
            path.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(xdg / "config"),
                "XDG_DATA_HOME": str(xdg / "data"),
                "XDG_CACHE_HOME": str(xdg / "cache"),
                "PYTHONUNBUFFERED": "1",
                "NO_COLOR": "1",
            }
        )
        self.env = env

    def _cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        if self.env is None:
            raise RuntimeError("worker has not been initialized")
        bm = environment_executable("bm")
        command = [str(bm), *args] if bm is not None else [sys.executable, "-m", "basic_memory.cli.main", *args]
        result = subprocess.run(
            command,
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                "Basic Memory CLI failed\n"
                f"command: {' '.join(command)}\n"
                f"exit: {result.returncode}\n"
                f"stdout:\n{result.stdout[-8000:]}\n"
                f"stderr:\n{result.stderr[-8000:]}"
            )
        return result

    @staticmethod
    def _project_name(corpus: str) -> str:
        return f"memory-eval-{corpus}"

    @staticmethod
    def _extract_json(text: str) -> Any:
        stripped = text.strip()
        if not stripped:
            return []
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        decoder = json.JSONDecoder()
        candidates: list[Any] = []
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            candidates.append(value)
        if not candidates:
            raise RuntimeError(f"Basic Memory returned no parseable JSON:\n{text[-8000:]}")
        return candidates[-1]

    @classmethod
    def _hits(cls, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item if isinstance(item, dict) else {"value": item} for item in payload]
        if not isinstance(payload, dict):
            return [{"value": payload}]
        for key in ("results", "items", "matches", "memories", "notes"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item if isinstance(item, dict) else {"value": item} for item in value]
            if isinstance(value, dict):
                nested = cls._hits(value)
                if nested:
                    return nested
        # Some CLI versions wrap the MCP-style result in `content` entries whose
        # `text` field is itself JSON.
        content = payload.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    try:
                        nested_payload = cls._extract_json(item["text"])
                    except RuntimeError:
                        continue
                    nested = cls._hits(nested_payload)
                    if nested:
                        return nested
        return [payload]

    def hello(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        help_result = self._cli("tool", "search-notes", "--help", check=False)
        if help_result.returncode != 0:
            raise RuntimeError(
                "Basic Memory search-notes CLI is not usable\n"
                f"stdout:\n{help_result.stdout[-4000:]}\n"
                f"stderr:\n{help_result.stderr[-4000:]}"
            )
        bm = environment_executable("bm")
        return {
            "backend": "basic-memory",
            "provider_version": self.provider_version,
            "python": sys.version.split()[0],
            "cli": str(bm) if bm is not None else f"{sys.executable} -m basic_memory.cli.main",
        }

    def ingest(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        corpus = str(request["corpus"])
        memory_root = Path(request["memory_root"]).resolve()
        project = self._project_name(corpus)
        documents = len(list(memory_root.rglob("*.md")))
        started = time.perf_counter()

        add = self._cli(
            "project",
            "add",
            project,
            str(memory_root),
            "--local",
            check=False,
        )
        if add.returncode != 0:
            combined = f"{add.stdout}\n{add.stderr}".casefold()
            if not any(marker in combined for marker in ("already", "exists", "configured")):
                raise RuntimeError(
                    "Basic Memory project registration failed\n"
                    f"stdout:\n{add.stdout[-8000:]}\n"
                    f"stderr:\n{add.stderr[-8000:]}"
                )

        reindex = self._cli("reindex", "-p", project)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "backend": "basic-memory",
            "provider_version": self.provider_version,
            "documents": documents,
            "elapsed_ms": elapsed_ms,
            "project": project,
            "metadata": {
                "source_of_truth": "markdown",
                "reindex_stdout_tail": reindex.stdout[-4000:],
                "reindex_stderr_tail": reindex.stderr[-4000:],
            },
        }

    def query(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        corpus = str(request["corpus"])
        query = str(request["query"])
        limit = int(request["limit"])
        project = self._project_name(corpus)
        started = time.perf_counter()

        args = [
            "tool",
            "search-notes",
            query,
            "--project",
            project,
            "--local",
            "--json",
            "--page-size",
            str(limit),
        ]
        result = self._cli(*args, check=False)
        if result.returncode != 0:
            # `--page-size` is recent. Retry without it so a patch remains usable
            # if Basic Memory changes this optional CLI flag while preserving the
            # JSON search tool.
            fallback_args = [
                "tool",
                "search-notes",
                query,
                "--project",
                project,
                "--local",
                "--json",
            ]
            result = self._cli(*fallback_args)
        payload = self._extract_json(result.stdout)
        hits = self._hits(payload)[:limit]
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "backend": "basic-memory",
            "provider_version": self.provider_version,
            "requested_limit": limit,
            "elapsed_ms": elapsed_ms,
            "retrieval_llm_calls": 0,
            "hits": hits,
            "metadata": {
                "project": project,
                "mode": "search-notes",
                "raw_result_type": type(payload).__name__,
                "stderr_tail": result.stderr[-2000:],
            },
        }

    def close(self) -> dict[str, Any]:
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
    worker = BasicMemoryWorker()
    serve(worker.handle)
