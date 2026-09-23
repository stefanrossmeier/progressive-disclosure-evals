from __future__ import annotations

import dataclasses
import json
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

# Backend libraries and CLIs are noisy. Reserve the original stdout exclusively
# for one JSON object per protocol request and send every incidental print/log to
# stderr instead.
PROTOCOL_STDOUT = sys.stdout
sys.stdout = sys.stderr


def environment_executable(name: str) -> Path | None:
    """Locate a console script installed alongside the worker's venv Python.

    Do not resolve ``sys.executable`` first: uv/pyenv-created virtualenvs often
    use a symlink to a shared interpreter, and resolving that symlink escapes
    the virtualenv and makes its console scripts appear to be missing.
    """
    candidates = [
        Path(sys.executable).parent / name,
        Path(sys.prefix) / "bin" / name,
        Path(sys.prefix) / "Scripts" / f"{name}.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    found = shutil.which(name)
    return Path(found) if found else None


def markdown_document_id(path: Path, body: str | None = None) -> str:
    """Return the canonical frontmatter id, falling back to the filename stem."""
    text = path.read_text(encoding="utf-8") if body is None else body
    if text.startswith("---"):
        end = text.find("\n---", 3)
        frontmatter = text[3:end] if end != -1 else text[:4096]
        match = re.search(r"(?m)^id:\s*(.+?)\s*$", frontmatter)
        if match:
            value = match.group(1).strip().strip("\"'")
            if value:
                return value
    return path.stem


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if dataclasses.is_dataclass(value):
        return jsonable(dataclasses.asdict(value))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return jsonable(model_dump(mode="json"))
    as_dict = getattr(value, "dict", None)
    if callable(as_dict):
        try:
            return jsonable(as_dict())
        except TypeError:
            pass
    if isinstance(value, dict):
        return {str(key): jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(child) for child in value]
    if hasattr(value, "__dict__"):
        return jsonable(vars(value))
    return str(value)


def emit(payload: dict[str, Any]) -> None:
    PROTOCOL_STDOUT.write(json.dumps(jsonable(payload), ensure_ascii=False) + "\n")
    PROTOCOL_STDOUT.flush()


def serve(handler: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise TypeError("protocol request must be a JSON object")
            response = handler(request)
            if not isinstance(response, dict):
                raise TypeError("worker handler must return a dict")
            emit({"ok": True, **response})
            if request.get("op") == "close":
                return
        except Exception as exc:  # noqa: BLE001 - protocol must report provider failures verbatim.
            emit(
                {
                    "ok": False,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            if isinstance(locals().get("request"), dict) and request.get("op") == "close":
                return
