#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

BASIC_MEMORY_VERSION="${BASIC_MEMORY_VERSION:-0.23.2}"
OPENVIKING_VERSION="${OPENVIKING_VERSION:-0.4.21}"
OPENVIKING_SDK_VERSION="${OPENVIKING_SDK_VERSION:-0.1.12}"
HINDSIGHT_VERSION="${HINDSIGHT_VERSION:-0.10.1}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "error: $PYTHON_BIN not found. Basic Memory requires Python 3.12+." >&2
  echo "Set PYTHON_BIN=/path/to/python3.12 and rerun." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ required for the backend environments; got {sys.version.split()[0]}")
PY

create_env() {
  local backend="$1"
  local env_dir="$ROOT/.venvs/$backend"
  if [[ ! -x "$env_dir/bin/python" ]]; then
    echo "==> creating $backend environment"
    "$PYTHON_BIN" -m venv "$env_dir"
  fi
  "$env_dir/bin/python" -m pip install --upgrade pip wheel setuptools
}

create_env basic-memory
"$ROOT/.venvs/basic-memory/bin/python" -m pip install "basic-memory==$BASIC_MEMORY_VERSION"

create_env openviking
"$ROOT/.venvs/openviking/bin/python" -m pip install \
  "openviking==$OPENVIKING_VERSION" \
  "openviking-sdk==$OPENVIKING_SDK_VERSION"

create_env hindsight
HINDSIGHT_PACKAGE="${HINDSIGHT_PACKAGE:-}"
if [[ -z "$HINDSIGHT_PACKAGE" ]]; then
  if [[ "$(uname -s)" == "Darwin" && "$(uname -m)" == "x86_64" ]]; then
    HINDSIGHT_PACKAGE="hindsight-all-slim==$HINDSIGHT_VERSION"
  else
    HINDSIGHT_PACKAGE="hindsight-all==$HINDSIGHT_VERSION"
  fi
fi
"$ROOT/.venvs/hindsight/bin/python" -m pip install "$HINDSIGHT_PACKAGE"

echo
echo "Installed isolated backend environments:"
"$ROOT/.venvs/basic-memory/bin/python" - <<'PY'
import importlib.metadata as m
print("  basic-memory:", m.version("basic-memory"))
PY
"$ROOT/.venvs/openviking/bin/python" - <<'PY'
import importlib.metadata as m
print("  openviking:", m.version("openviking"), "sdk:", m.version("openviking-sdk"))
PY
"$ROOT/.venvs/hindsight/bin/python" - <<'PY'
import importlib.metadata as m
for name in ("hindsight-all", "hindsight-all-slim", "hindsight-client"):
    try:
        print("  hindsight:", name, m.version(name))
        break
    except m.PackageNotFoundError:
        pass
PY
