#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from _common import markdown_document_id, serve

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / ".tools" / "ai-memory"

_FTS_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does",
    "for", "from", "had", "has", "have", "how", "in", "into", "is", "it",
    "of", "on", "or", "that", "the", "this", "to", "was", "were", "what",
    "when", "where", "which", "who", "why", "with",
}


def _fts_terms(question: str) -> list[str]:
    """Return deterministic lexical terms for ai-memory's FTS5 search."""
    tokens = re.findall(r"[A-Za-z0-9]+(?:[-_/][A-Za-z0-9]+)*", question)
    retained: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        folded = token.casefold()
        if folded in seen or folded in _FTS_STOPWORDS:
            continue
        if len(token) < 3 and not any(ch.isdigit() for ch in token):
            continue
        seen.add(folded)
        retained.append(token)
    return retained or tokens[:1] or [question.strip()]


def _quote_fts_term(token: str) -> str:
    return '"' + token.replace('"', '""') + '"'


def _fts_query(question: str) -> str:
    """Convert a natural-language question to a safe FTS5 OR expression."""
    return " OR ".join(_quote_fts_term(token) for token in _fts_terms(question)[:20])



def _pick_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class AiMemoryWorker:
    def __init__(self) -> None:
        self.runtime_root: Path | None = None
        self.env: dict[str, str] | None = None
        self.process: subprocess.Popen[str] | None = None
        self.port: int | None = None
        self.corpus: str | None = None

    def _configure(self, runtime_root: str, corpus: str | None = None) -> None:
        root = Path(runtime_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        if self.process and self.process.poll() is None and corpus != self.corpus:
            self.close()
        self.runtime_root = root
        self.corpus = corpus
        env = os.environ.copy()
        # Keep the benchmark isolated from any personal/remote ai-memory setup.
        # The harness owns a loopback-only, unauthenticated server per corpus.
        env.pop("AI_MEMORY_SERVER_URL", None)
        env.pop("AI_MEMORY_AUTH_TOKEN", None)
        store_name = corpus if corpus is not None else "bootstrap"
        env["AI_MEMORY_DATA_DIR"] = str(root / "stores" / store_name)
        env["AI_MEMORY_EMBEDDING_PROVIDER"] = "none"
        env["NO_COLOR"] = "1"
        self.env = env

    def _cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(BIN), *args],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode:
            raise RuntimeError(
                f"ai-memory failed: {' '.join(args)}\n"
                f"stdout:\n{result.stdout[-4000:]}\nstderr:\n{result.stderr[-4000:]}"
            )
        return result

    def _ensure_server(self) -> None:
        if self.process and self.process.poll() is None:
            return
        assert self.env is not None
        self.port = _pick_port()
        self.env["AI_MEMORY_SERVER_URL"] = f"http://127.0.0.1:{self.port}"
        self._cli("init", check=False)
        assert self.runtime_root is not None
        log_path = self.runtime_root / "ai-memory-server.log"
        with log_path.open("a", encoding="utf-8") as log_handle:
            self.process = subprocess.Popen(
                [
                    str(BIN),
                    "serve",
                    "--transport",
                    "http",
                    "--bind",
                    f"127.0.0.1:{self.port}",
                    # /api/v1 is mounted only when the web surface is enabled.
                    "--enable-web",
                    # The server creates its fallback workspace/project at
                    # startup.  Pin that scope to the corpus so admin writes
                    # with no per-request override land in the same project
                    # that the read/search API verifies later.
                    "--workspace",
                    "default",
                    "--project",
                    str(self.corpus),
                ],
                env=self.env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        probe_url = f"http://127.0.0.1:{self.port}/api/v1/workspaces"
        for _ in range(100):
            if self.process.poll() is not None:
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-6000:]
                raise RuntimeError(
                    f"ai-memory server exited during startup with code {self.process.returncode}\n"
                    f"server log:\n{tail}"
                )
            try:
                urllib.request.urlopen(probe_url, timeout=0.25).read()
                return
            except Exception:
                time.sleep(0.1)
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-6000:]
        self.close()
        raise RuntimeError(
            f"ai-memory server did not become reachable at {probe_url}\nserver log:\n{tail}"
        )

    def _version(self) -> str:
        result = self._cli("--version", check=False)
        return result.stdout.strip() or result.stderr.strip() or "unknown"

    def hello(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        return {"backend": "ai-memory", "provider_version": self._version(), "cli": str(BIN)}

    def ingest(self, request: dict[str, Any]) -> dict[str, Any]:
        corpus = str(request["corpus"])
        self._configure(str(request["runtime_root"]), corpus)
        memory_root = Path(request["memory_root"]).resolve()
        # ai-memory's CLI is a thin HTTP client for state-changing commands.
        # Keep a corpus-local loopback server alive while write-page ingests the
        # prepared Markdown, then reuse the same server for FTS queries.
        self._ensure_server()
        started = time.perf_counter()
        count = 0
        for path in sorted(memory_root.rglob("*.md")):
            body = path.read_text(encoding="utf-8")
            document_id = markdown_document_id(path, body)
            relative = path.relative_to(memory_root).as_posix()
            text = (
                f"# {document_id}\n\n"
                f"Document-ID: {document_id}\n"
                f"Source-Path: {relative}\n\n{body}"
            )
            # Use ai-memory's public operator mutation API directly.  The
            # native CLI is intentionally a thin HTTP client, but routing it
            # through another subprocess made scope failures unnecessarily
            # opaque in the benchmark.  The corpus scope is pinned when the
            # server starts, so these writes deliberately omit scope overrides.
            write_result = self._api_post(
                "/admin/write-page",
                {
                    # ai-memory 2.4.0 requires explicit workspace/project in
                    # the admin write request even when serve was started with
                    # the same fallback scope. Keep both layers aligned.
                    "workspace": "default",
                    "project": corpus,
                    "path": f"notes/{document_id}.md",
                    "body": text,
                    "pinned": True,
                },
            )
            if isinstance(write_result, dict) and write_result.get("ok") is False:
                raise RuntimeError(
                    "ai-memory write-page returned ok=false for "
                    f"{document_id}: {json.dumps(write_result, sort_keys=True)}"
                )
            count += 1

        pages_payload = self._api_get(
            f"/api/v1/workspaces/default/projects/{urllib.parse.quote(corpus, safe='')}/pages"
        )
        pages = self._api_list(pages_payload, "pages")
        projects_payload = self._api_get("/api/v1/projects", {"workspace": "default"})
        projects = self._api_list(projects_payload, "projects")
        if not isinstance(pages, list) or len(pages) != count:
            project_summary = [
                {
                    "workspace_name": item.get("workspace_name"),
                    "project_name": item.get("project_name"),
                    "page_count": item.get("page_count"),
                }
                for item in projects
                if isinstance(item, dict)
            ]
            raise RuntimeError(
                "ai-memory import verification failed: "
                f"expected {count} pages in default/{corpus}, found "
                f"{len(pages) if isinstance(pages, list) else 'unknown'}; "
                f"visible projects={project_summary}"
            )
        return {
            "backend": "ai-memory",
            "provider_version": self._version(),
            "documents": count,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "metadata": {
                "mode": "write-page + corpus-local FTS5 API search",
                "server_scope": f"default/{corpus}",
                "embedding_provider": "none",
                "source_of_truth": "ai-memory git-backed markdown wiki",
            },
        }

    def _api_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        assert self.port is not None
        url = f"http://127.0.0.1:{self.port}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"} if data is not None else {}
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"ai-memory HTTP {method} {path} failed with {exc.code}: {body[-4000:]}"
            ) from exc
        if not raw:
            return {}
        return json.loads(raw)

    def _api_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._api_request("GET", path, params=params)

    def _api_post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._api_request("POST", path, payload=payload)

    @staticmethod
    def _api_list(payload: Any, legacy_key: str) -> list[Any]:
        """Accept ai-memory 2.4 bare arrays and older wrapped list responses."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            value = payload.get(legacy_key, [])
            return value if isinstance(value, list) else []
        return []

    def _search(self, corpus: str, query: str, limit: int) -> list[dict[str, Any]]:
        payload = self._api_get(
            "/api/v1/search",
            {
                "q": query,
                "limit": limit,
                "workspace": "default",
                "project": corpus,
            },
        )
        raw_hits = self._api_list(payload, "hits")
        return [hit for hit in raw_hits if isinstance(hit, dict)]

    @staticmethod
    def _decorate_hit(raw_hit: dict[str, Any]) -> dict[str, Any]:
        hit = dict(raw_hit)
        provider_path = hit.get("path")
        if isinstance(provider_path, str):
            name = Path(provider_path).name
            if name.endswith(".md"):
                hit["document_id"] = name[:-3]
        return hit

    def query(self, request: dict[str, Any]) -> dict[str, Any]:
        corpus = str(request["corpus"])
        self._configure(str(request["runtime_root"]), corpus)
        self._ensure_server()
        limit = int(request["limit"])
        started = time.perf_counter()
        question = str(request["query"])
        terms = _fts_terms(question)[:20]
        search_query = " OR ".join(_quote_fts_term(token) for token in terms)
        raw_hits = self._search(corpus, search_query, limit)

        # ai-memory's public FTS surface accepts FTS5 syntax, but releases and
        # tokenizers have changed over time.  If a composed OR query yields no
        # candidates, probe the exact same native FTS index one term at a time
        # and fuse those provider-ranked hits deterministically.  This is not a
        # local grep fallback: every candidate still comes from ai-memory.
        fallback_used = False
        fallback_queries: list[str] = []
        if not raw_hits:
            fallback_used = True
            fused: dict[str, dict[str, Any]] = {}
            for token in terms[:12]:
                token_query = _quote_fts_term(token)
                fallback_queries.append(token_query)
                for provider_rank, candidate in enumerate(
                    self._search(corpus, token_query, max(limit, 10)), start=1
                ):
                    path = str(candidate.get("path") or candidate.get("id") or json.dumps(candidate, sort_keys=True))
                    entry = fused.setdefault(
                        path,
                        {"hit": dict(candidate), "score": 0.0, "matched_queries": []},
                    )
                    entry["score"] += 1.0 / (60.0 + provider_rank)
                    entry["matched_queries"].append(token)
            ranked = sorted(
                fused.values(),
                key=lambda item: (-float(item["score"]), str(item["hit"].get("path", ""))),
            )
            raw_hits = []
            for item in ranked[:limit]:
                hit = dict(item["hit"])
                hit["score"] = float(item["score"])
                hit["matched_queries"] = list(item["matched_queries"])
                raw_hits.append(hit)

        pages_payload = self._api_get(
            f"/api/v1/workspaces/default/projects/{urllib.parse.quote(corpus, safe='')}/pages"
        )
        pages = self._api_list(pages_payload, "pages")
        projects_payload = self._api_get("/api/v1/projects", {"workspace": "default"})
        projects = self._api_list(projects_payload, "projects")
        hits = [self._decorate_hit(hit) for hit in raw_hits[:limit]]
        return {
            "backend": "ai-memory",
            "provider_version": self._version(),
            "requested_limit": limit,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "retrieval_llm_calls": 0,
            "hits": hits,
            "metadata": {
                "mode": "corpus_local_fts5_api_search",
                "workspace": "default",
                "project": corpus,
                "fts_query": search_query,
                "fallback_used": fallback_used,
                "fallback_queries": fallback_queries,
                "indexed_page_count": len(pages) if isinstance(pages, list) else None,
                "visible_projects": [
                    {
                        "workspace_name": item.get("workspace_name"),
                        "project_name": item.get("project_name"),
                        "page_count": item.get("page_count"),
                    }
                    for item in projects
                    if isinstance(item, dict)
                ],
            },
        }

    def close(self) -> dict[str, Any]:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        return {"closed": True}

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        if request["op"] == "close":
            return self.close()
        return {"hello": self.hello, "ingest": self.ingest, "query": self.query}[request["op"]](request)


if __name__ == "__main__":
    serve(AiMemoryWorker().handle)
