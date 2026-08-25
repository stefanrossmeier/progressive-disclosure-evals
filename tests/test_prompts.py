from pathlib import Path

import pytest

from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.prompts import (
    DEFAULT_AGENT_PROMPT_PATH,
    build_evidence_state,
    build_selection_state,
    load_prompt_artifact,
)


def test_default_prompt_is_version_18():
    artifact = load_prompt_artifact()
    assert artifact.version == 18
    assert DEFAULT_AGENT_PROMPT_PATH == Path("prompts/agent/system-v18.md")


def test_v18_prompt_is_lean_and_requires_complete_evidence_planning():
    lower = load_prompt_artifact().content.lower()
    assert "metadata" in lower
    assert "routing" in lower
    assert "evidence" in lower
    assert "non-x" in lower
    assert "without x" in lower
    assert "complete evidence plan" in lower
    assert "do not retrieve a document solely" in lower
    assert "source labels or navigation hints, not answer values" in lower
    assert "different independent clause" in lower
    assert len(load_prompt_artifact().content) < 3000


def test_previous_prompt_artifacts_remain_versioned():
    for version in range(1, 18):
        assert load_prompt_artifact(f"prompts/agent/system-v{version}.md").version == version


def test_prompt_loader_rejects_missing_frontmatter(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("plain", encoding="utf-8")
    with pytest.raises(ValueError, match="front matter"):
        load_prompt_artifact(path)


def test_selection_state_contains_metadata_but_not_unopened_body_or_paths():
    kb = KnowledgeBase("corpus/northstar-corpus")
    state = build_selection_state(question="What applies to MIG-2?", catalog=kb.catalog())
    assert "commercial.billing.credits.migration" in state
    assert "Migration Credits" in state
    assert "MIG-2" in state  # routing vocabulary is intentionally in activation metadata
    assert "SABLE-88" not in state  # answer fact remains hidden
    assert "path=" not in state


def test_evidence_state_discloses_only_selected_body():
    kb = KnowledgeBase("corpus/northstar-corpus")
    doc = kb.read("commercial.billing.credits.migration")
    state = build_evidence_state(question="MIG-2?", opened_documents=(doc,))
    assert "SABLE-88" in state
    assert "commercial.billing.refunds.standard" in state  # ordinary body cross-reference
    assert "AVAILABLE DOCUMENT METADATA" not in state


def test_selection_state_warns_that_negative_qualifiers_are_local():
    kb = KnowledgeBase("corpus/northstar-corpus")
    state = build_selection_state(
        question="US-governed standard refund; no D-8 exception applies.",
        catalog=kb.catalog(),
    )
    assert "never flatten clause-local scope into global qualifiers" in state.lower()
    assert "`non-x` as excluding x" in state.lower()
    assert "atomic evidence obligation" in state.lower()


def test_evidence_state_carries_nonfactual_routing_plan():
    kb = KnowledgeBase("corpus/northstar-corpus")
    doc = kb.read("platform.products.zephyr.limits")
    state = build_evidence_state(
        question="What remains assigned?",
        opened_documents=(doc,),
        evidence_plan=(("establish Zephyr base tier", "platform.products.zephyr.limits"),),
    )
    assert "EVIDENCE OBLIGATIONS FROM ROUTING PLAN" in state
    assert "- establish Zephyr base tier" in state
    assert "establish Zephyr base tier -> platform.products.zephyr.limits" not in state
    assert "source labels rather than factual answer values" in state


def test_v18_prompt_is_corpus_neutral_and_routes_by_entity_anchors():
    artifact = load_prompt_artifact()
    lower = artifact.content.lower()
    assert artifact.version == 18
    assert "northstar" not in lower
    assert "entity anchors" in lower
    assert "assumed document taxonomy" in lower
    assert "corroboration" in lower
    assert "different independent clause" in lower
    assert "source labels or navigation hints, not answer values" in lower


def test_runtime_selection_state_is_corpus_neutral():
    kb = KnowledgeBase("corpus/tell-aster")
    state = build_selection_state(question="Where was SF-241 recovered?", catalog=kb.catalog())
    lower = state.lower()
    assert "sf-241" in lower
    assert "northstar" not in lower
    assert "default/normal/base" not in lower
    assert "regional/effective" not in lower
    assert "entity anchors" in lower
    assert "document family" in lower


def test_selection_state_preserves_clause_local_obligation_wording():
    kb = KnowledgeBase("corpus/northstar-corpus")
    state = build_selection_state(
        question="What is the ordinary Atlas outage cap, and which team governs MIG-2 migration credit?",
        catalog=kb.catalog(),
    ).casefold()
    assert "make each obligation self-contained" in state
    assert "counterfactual" in state
    assert "another independent clause" in state


def test_recovery_selection_state_exposes_observed_references_as_hints_not_evidence():
    kb = KnowledgeBase("corpus/tell-aster")
    state = build_selection_state(
        question="Which source owns the missing date?",
        catalog=kb.catalog(),
        already_opened=("TA-CER-08",),
        missing_information="Need the broad absolute range for the revised ceramic horizon.",
        discovered_references=("TA-SYN-05",),
    )
    assert "REFERENCES OBSERVED IN DISCLOSED BODIES" in state
    assert "TA-SYN-05" in state
    assert "routing hints only; not factual evidence" in state
    assert "do not follow them merely because they were linked" in state


def test_evidence_state_resolves_compound_branches_independently():
    kb = KnowledgeBase("corpus/northstar-corpus")
    docs = (
        kb.read("operations.incidents.escalation.routing"),
        kb.read("governance.regions.eu.data-handling"),
    )
    state = build_evidence_state(
        question="Give the Atlas default queue without a regional replacement and the EU effective queue.",
        opened_documents=docs,
        evidence_plan=(
            ("Atlas default queue without a regional replacement", "operations.incidents.escalation.routing"),
            ("EU effective Atlas queue", "governance.regions.eu.data-handling"),
        ),
    ).casefold()
    assert "resolve obligations independently" in state
    assert "must not overwrite" in state
    assert "counterfactual branch" in state
