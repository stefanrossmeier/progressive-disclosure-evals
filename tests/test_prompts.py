from pathlib import Path

import pytest

from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.prompts import (
    DEFAULT_AGENT_PROMPT_PATH,
    build_evidence_state,
    build_selection_state,
    load_prompt_artifact,
)


def test_default_prompt_is_version_14():
    artifact = load_prompt_artifact()
    assert artifact.version == 14
    assert DEFAULT_AGENT_PROMPT_PATH == Path("prompts/agent/system-v14.md")


def test_v14_prompt_is_lean_and_requires_complete_evidence_planning():
    lower = load_prompt_artifact().content.lower()
    assert "metadata" in lower
    assert "routing" in lower
    assert "evidence" in lower
    assert "negated scope" in lower
    assert "complete evidence plan" in lower
    assert "do not retrieve a document solely" in lower
    assert len(load_prompt_artifact().content) < 2600


def test_previous_prompt_artifacts_remain_versioned():
    for version in range(1, 14):
        assert load_prompt_artifact(f"prompts/agent/system-v{version}.md").version == version


def test_prompt_loader_rejects_missing_frontmatter(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("plain", encoding="utf-8")
    with pytest.raises(ValueError, match="front matter"):
        load_prompt_artifact(path)


def test_selection_state_contains_metadata_but_not_unopened_body_or_paths():
    kb = KnowledgeBase("corpus/northstar")
    state = build_selection_state(question="What applies to MIG-2?", catalog=kb.catalog())
    assert "commercial.billing.credits.migration" in state
    assert "Migration Credits" in state
    assert "MIG-2" in state  # routing vocabulary is intentionally in activation metadata
    assert "SABLE-88" not in state  # answer fact remains hidden
    assert "path=" not in state


def test_evidence_state_discloses_only_selected_body():
    kb = KnowledgeBase("corpus/northstar")
    doc = kb.read("commercial.billing.credits.migration")
    state = build_evidence_state(question="MIG-2?", opened_documents=(doc,))
    assert "SABLE-88" in state
    assert "commercial.billing.refunds.standard" in state  # ordinary body cross-reference
    assert "AVAILABLE DOCUMENT METADATA" not in state


def test_selection_state_warns_that_negative_qualifiers_are_local():
    kb = KnowledgeBase("corpus/northstar")
    state = build_selection_state(
        question="US-governed standard refund; no D-8 exception applies.",
        catalog=kb.catalog(),
    )
    assert "negative qualifier excludes only that branch" in state.lower()
    assert "atomic evidence obligation" in state.lower()


def test_evidence_state_carries_nonfactual_routing_plan():
    kb = KnowledgeBase("corpus/northstar")
    doc = kb.read("platform.products.zephyr.limits")
    state = build_evidence_state(
        question="What remains assigned?",
        opened_documents=(doc,),
        evidence_plan=(("establish Zephyr base tier", "platform.products.zephyr.limits"),),
    )
    assert "EVIDENCE OBLIGATIONS FROM ROUTING PLAN" in state
    assert "establish Zephyr base tier -> platform.products.zephyr.limits" in state
