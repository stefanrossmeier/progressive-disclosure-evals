from pathlib import Path

from progressive_disclosure.prompts import load_prompt_artifact


def test_versioned_agent_prompt_is_committed_under_prompts_directory():
    path = Path("prompts/agent/system-v7.md")
    assert path.is_file()
    artifact = load_prompt_artifact(path)
    assert artifact.version == 7
    assert artifact.id == "progressive-disclosure-agent-system"
