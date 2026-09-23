#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
AI_MEMORY_VERSION="${AI_MEMORY_VERSION:-2.4.0}"
EVEROS_VERSION="${EVEROS_VERSION:-1.3.1}"
AGENT_MEMORY_REF="${AGENT_MEMORY_REF:-main}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "error: $PYTHON_BIN not found; EverOS and agent-memory require Python 3.12+." >&2
  exit 1
fi
"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12+ required; got {sys.version.split()[0]}")
PY

mkdir -p "$ROOT/.tools" "$ROOT/.venvs"

# ai-memory: install a pinned release binary into the experiment, not globally.
if [[ ! -x "$ROOT/.tools/ai-memory" ]]; then
  os="$(uname -s)"; arch="$(uname -m)"
  case "$os/$arch" in
    Darwin/arm64) asset="ai-memory-macos-aarch64.tar.gz" ;;
    Darwin/x86_64) asset="ai-memory-macos-x86_64.tar.gz" ;;
    Linux/x86_64) asset="ai-memory-linux-x86_64.tar.gz" ;;
    Linux/aarch64|Linux/arm64) asset="ai-memory-linux-aarch64.tar.gz" ;;
    *) echo "unsupported platform for prebuilt ai-memory: $os/$arch" >&2; exit 1 ;;
  esac
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  base="https://github.com/akitaonrails/ai-memory/releases/download/v${AI_MEMORY_VERSION}"
  curl -fsSL "$base/$asset" -o "$tmp/$asset"
  curl -fsSL "$base/$asset.sha256" -o "$tmp/$asset.sha256"
  (cd "$tmp" && shasum -a 256 -c "$asset.sha256")
  tar -xzf "$tmp/$asset" -C "$tmp"
  bin="$(find "$tmp" -type f -name ai-memory -perm -111 | head -1)"
  [[ -n "$bin" ]] || { echo "ai-memory binary not found in release asset" >&2; exit 1; }
  cp "$bin" "$ROOT/.tools/ai-memory"; chmod +x "$ROOT/.tools/ai-memory"
fi

create_env() {
  local backend="$1"; local env_dir="$ROOT/.venvs/$backend"
  if [[ ! -x "$env_dir/bin/python" ]]; then "$PYTHON_BIN" -m venv "$env_dir"; fi
  "$env_dir/bin/python" -m pip install --upgrade pip wheel setuptools
}

create_env everos
"$ROOT/.venvs/everos/bin/python" -m pip install "everos==$EVEROS_VERSION"

# agent-memory has no PyPI release. Keep an exact source checkout under .tools;
# bootstrap resolves the requested ref once and records the resulting SHA.
if [[ ! -d "$ROOT/.tools/agent-memory/.git" ]]; then
  git clone https://github.com/tigerless-labs/agent-memory.git "$ROOT/.tools/agent-memory"
fi
git -C "$ROOT/.tools/agent-memory" fetch --tags origin
git -C "$ROOT/.tools/agent-memory" checkout --detach "$AGENT_MEMORY_REF"
AGENT_MEMORY_SHA="$(git -C "$ROOT/.tools/agent-memory" rev-parse HEAD)"
if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is required for agent-memory (https://docs.astral.sh/uv/)." >&2
  exit 1
fi
(cd "$ROOT/.tools/agent-memory" && uv sync --all-packages)
printf '%s\n' "$AGENT_MEMORY_SHA" > "$ROOT/.tools/agent-memory.sha"

# The harness expects one Python executable per worker. ai-memory and agent-memory
# workers only shell out to pinned CLIs, so small stdlib-only venvs are enough.
create_env ai-memory
create_env agent-memory

echo "Installed backend versions:"
"$ROOT/.tools/ai-memory" --version || true
"$ROOT/.venvs/everos/bin/python" - <<'PY'
import importlib.metadata as m
print("everos", m.version("everos"))
PY
echo "agent-memory $AGENT_MEMORY_SHA"
