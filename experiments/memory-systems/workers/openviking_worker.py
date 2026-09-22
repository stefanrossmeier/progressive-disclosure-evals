#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from _common import environment_executable, jsonable, serve


class OpenVikingWorker:
    def __init__(self) -> None:
        self.runtime_root: Path | None = None
        self.provider_version = importlib.metadata.version("openviking")
        self.sdk_version = importlib.metadata.version("openviking-sdk")
        self.port = int(os.getenv("MEMORY_EVAL_OPENVIKING_PORT", "19331"))
        self.server: subprocess.Popen[str] | None = None
        self.server_log_handle: Any = None
        self.client: Any = None
        self.config_path: Path | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _configure(self, runtime_root: str) -> None:
        root = Path(runtime_root).resolve()
        if self.runtime_root == root and self.config_path is not None:
            return
        self.runtime_root = root
        home = root / "home"
        workspace = root / "workspace"
        home.mkdir(parents=True, exist_ok=True)
        workspace.mkdir(parents=True, exist_ok=True)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenViking experiment")
        ingest_model = (
            os.getenv("MEMORY_EVAL_INGEST_MODEL")
            or os.getenv("MEMORY_EVAL_OPENVIKING_VLM_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-5-nano"
        )
        embedding_model = os.getenv("MEMORY_EVAL_OPENVIKING_EMBEDDING_MODEL", "text-embedding-3-small")
        embedding_dimension = int(os.getenv("MEMORY_EVAL_OPENVIKING_EMBEDDING_DIMENSION", "1536"))
        config = {
            "storage": {
                "workspace": str(workspace),
                "vectordb": {"name": "context", "backend": "local"},
                "agfs": {"backend": "local"},
            },
            "embedding": {
                "text_source": "content_only",
                "dense": {
                    "api_base": "https://api.openai.com/v1",
                    "api_key": api_key,
                    "provider": "openai",
                    "dimension": embedding_dimension,
                    "model": embedding_model,
                },
            },
            "vlm": {
                "api_base": "https://api.openai.com/v1",
                "api_key": api_key,
                "provider": "openai",
                "model": ingest_model,
            },
            "server": {
                "host": "127.0.0.1",
                "port": self.port,
                "auth_mode": "dev",
                "root_api_key": None,
                "agent_evolution": {"enabled": False},
            },
        }
        self.config_path = root / "ov.conf"
        self.config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    def _server_env(self) -> dict[str, str]:
        if self.runtime_root is None or self.config_path is None:
            raise RuntimeError("worker is not configured")
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.runtime_root / "home"),
                "OPENVIKING_CONFIG_FILE": str(self.config_path),
                "PYTHONUNBUFFERED": "1",
                "NO_COLOR": "1",
            }
        )
        return env

    def _log_tail(self, size: int = 12000) -> str:
        if self.runtime_root is None:
            return ""
        path = self.runtime_root / "openviking-server.log"
        if not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[-size:]

    def _server_executable(self) -> Path:
        executable = environment_executable("openviking-server")
        if executable is None:
            raise RuntimeError(
                "OpenViking server executable not found in the backend environment; "
                f"python={sys.executable} prefix={sys.prefix}"
            )
        return executable

    def _ensure_server(self) -> None:
        if self.server is not None and self.server.poll() is None and self.client is not None:
            return
        if self.runtime_root is None or self.config_path is None:
            raise RuntimeError("worker has not been initialized")
        executable = self._server_executable()
        log_path = self.runtime_root / "openviking-server.log"
        self.server_log_handle = log_path.open("a", encoding="utf-8")
        self.server = subprocess.Popen(
            [str(executable), "--config", str(self.config_path)],
            stdout=self.server_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=self._server_env(),
        )
        deadline = time.monotonic() + 120.0
        last_error = ""
        while time.monotonic() < deadline:
            if self.server.poll() is not None:
                raise RuntimeError(
                    f"OpenViking server exited with {self.server.returncode}\n{self._log_tail()}"
                )
            try:
                with urllib.request.urlopen(f"{self.url}/health", timeout=2.0) as response:  # noqa: S310
                    if 200 <= response.status < 300:
                        break
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
                time.sleep(0.5)
        else:
            raise RuntimeError(
                f"OpenViking server did not become healthy: {last_error}\n{self._log_tail()}"
            )

        from openviking_sdk import SyncHTTPClient

        self.client = SyncHTTPClient(url=self.url)
        self.client.initialize()

    @staticmethod
    def _target(corpus: str) -> str:
        return f"viking://resources/memory-eval/{corpus}/"

    @staticmethod
    def _resource_hits(payload: Any) -> list[dict[str, Any]]:
        data = jsonable(payload)
        if isinstance(data, dict):
            for key in ("resources", "result"):
                value = data.get(key)
                if key == "result" and isinstance(value, dict):
                    nested = OpenVikingWorker._resource_hits(value)
                    if nested:
                        return nested
                if isinstance(value, list):
                    return [item if isinstance(item, dict) else {"value": item} for item in value]
        if isinstance(data, list):
            return [item if isinstance(item, dict) else {"value": item} for item in data]
        return [{"value": data}] if data is not None else []

    def hello(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        # Start lazily; doctor/hello should not spend model/API calls. Still
        # validate that the server console script exists in this virtualenv.
        executable = self._server_executable()
        return {
            "backend": "openviking",
            "provider_version": self.provider_version,
            "sdk_version": self.sdk_version,
            "python": sys.version.split()[0],
            "server_executable": str(executable),
            "url": self.url,
        }

    def ingest(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        self._ensure_server()
        corpus = str(request["corpus"])
        memory_root = Path(request["memory_root"]).resolve()
        target = self._target(corpus)
        documents = len(list(memory_root.rglob("*.md")))

        # Re-ingest is authoritative: remove prior derived state at this URI. The
        # Markdown snapshot outside OpenViking remains the source used to rebuild it.
        try:
            self.client.rm(target, recursive=True)
        except Exception:  # noqa: BLE001 - not-existing is the expected first-run case.
            pass

        processing_mode = os.getenv("MEMORY_EVAL_OPENVIKING_PROCESSING_MODE", "semantic_and_vectors").strip()
        options: dict[str, Any] = {"args": {"parse_mode": "no_split"}}
        if processing_mode:
            options["processing_mode"] = processing_mode
        started = time.perf_counter()
        result = self.client.add_resource(
            path=str(memory_root),
            to=target,
            wait=True,
            options=options,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "backend": "openviking",
            "provider_version": self.provider_version,
            "sdk_version": self.sdk_version,
            "documents": documents,
            "elapsed_ms": elapsed_ms,
            "target_uri": target,
            "metadata": {
                "processing_mode": processing_mode or "provider_default",
                "parse_mode": "no_split",
                "add_resource_result": jsonable(result),
                "server_log_tail": self._log_tail(4000),
            },
        }

    def query(self, request: dict[str, Any]) -> dict[str, Any]:
        self._configure(str(request["runtime_root"]))
        self._ensure_server()
        corpus = str(request["corpus"])
        query = str(request["query"])
        limit = int(request["limit"])
        target = self._target(corpus)
        started = time.perf_counter()
        result = self.client.find(
            query=query,
            target_uri=target,
            limit=limit,
            options={"level": [2]},
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        hits = self._resource_hits(result)[:limit]
        return {
            "backend": "openviking",
            "provider_version": self.provider_version,
            "requested_limit": limit,
            "elapsed_ms": elapsed_ms,
            "retrieval_llm_calls": 0,
            "hits": hits,
            "metadata": {
                "target_uri": target,
                "retrieval_method": "find",
                "level": [2],
            },
        }

    def close(self) -> dict[str, Any]:
        if self.client is not None:
            close = getattr(self.client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
            self.client = None
        if self.server is not None and self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=10)
        self.server = None
        if self.server_log_handle is not None:
            self.server_log_handle.close()
            self.server_log_handle = None
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
    worker = OpenVikingWorker()
    try:
        serve(worker.handle)
    finally:
        worker.close()
