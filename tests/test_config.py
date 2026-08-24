from __future__ import annotations

import os
from pathlib import Path

from progressive_disclosure.config import (
    get_openai_model, get_openai_reasoning_effort, get_openai_text_verbosity,
    has_openai_api_key, load_project_env,
)


def test_load_project_env_uses_openai_variable_names(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=test-key\nOPENAI_MODEL=test-nano\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    loaded = load_project_env(env_file)

    assert loaded == env_file
    assert os.getenv("OPENAI_API_KEY") == "test-key"
    assert get_openai_model() == "test-nano"
    assert has_openai_api_key() is True


def test_load_project_env_does_not_override_exported_values(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_MODEL=file-model\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_MODEL", "shell-model")

    load_project_env(env_file)

    assert get_openai_model() == "shell-model"


def test_missing_api_key_is_reported(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert has_openai_api_key() is False


def test_openai_runtime_tuning_has_low_cost_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("OPENAI_TEXT_VERBOSITY", raising=False)
    assert get_openai_reasoning_effort() == "low"
    assert get_openai_text_verbosity() == "low"
