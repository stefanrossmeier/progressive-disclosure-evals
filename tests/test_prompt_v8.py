from progressive_disclosure.prompts import load_prompt_artifact


def test_v8_is_compatible_metadata_first_prompt():
    prompt = load_prompt_artifact("prompts/agent/system-v8.md")
    assert prompt.version == 8
    lower = prompt.content.lower()
    assert "document catalog" in lower
    assert "read_document" in prompt.content
    assert "submit" in lower
    assert "do not read neighboring" in lower
