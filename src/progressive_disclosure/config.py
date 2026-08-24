from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"


def load_project_env(env_file: Path | None = None) -> Path:
    """Load repository-local environment variables without overriding exported values."""
    path = env_file or DEFAULT_ENV_FILE
    load_dotenv(dotenv_path=path, override=False)
    return path


def get_openai_model() -> str | None:
    return os.getenv("OPENAI_MODEL")


def get_openai_reasoning_effort() -> str:
    return os.getenv("OPENAI_REASONING_EFFORT", "low")


def get_openai_text_verbosity() -> str:
    return os.getenv("OPENAI_TEXT_VERBOSITY", "low")


def has_openai_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
