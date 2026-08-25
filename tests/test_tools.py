import pytest

from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.tools import (
    build_request_more_evidence_tool,
    build_select_documents_tool,
    build_submit_answer_tool,
    force_tool,
)


def test_select_documents_tool_is_strict_and_enumerates_available_documents():
    catalog = KnowledgeBase("corpus/northstar-corpus").catalog()[:2]
    tool = build_select_documents_tool(catalog, max_documents=2)
    assert tool["name"] == "select_documents"
    assert tool["strict"] is True
    primary = tool["parameters"]["properties"]["primary_document_id"]
    evidence_plan = tool["parameters"]["properties"]["evidence_plan"]
    assert primary["enum"] == [x.id for x in catalog]
    assert evidence_plan["items"]["properties"]["document_id"]["enum"] == [x.id for x in catalog]
    assert tool["parameters"]["additionalProperties"] is False


def test_select_documents_tool_rejects_empty_catalog():
    with pytest.raises(ValueError, match="at least one"):
        build_select_documents_tool((), max_documents=1)


def test_submit_answer_tool_requires_actual_answer_field():
    tool = build_submit_answer_tool()
    assert tool["name"] == "submit_answer"
    assert tool["strict"] is True
    assert tool["parameters"]["required"] == ["answer"]
    assert set(tool["parameters"]["properties"]) == {"answer"}


def test_request_more_evidence_tool_requires_precise_gap_field():
    tool = build_request_more_evidence_tool()
    assert tool["name"] == "request_more_evidence"
    assert tool["strict"] is True
    assert tool["parameters"]["required"] == ["missing_information"]
    assert set(tool["parameters"]["properties"]) == {"missing_information"}


def test_force_tool_shape():
    assert force_tool("select_documents") == {"type": "function", "name": "select_documents"}


def test_select_documents_tool_keeps_scope_in_local_evidence_needs_only():
    catalog = KnowledgeBase("corpus/northstar-corpus").catalog()[:2]
    tool = build_select_documents_tool(catalog, max_documents=2)
    required = tool["parameters"]["required"]
    properties = tool["parameters"]["properties"]
    assert set(required) == {"evidence_plan", "primary_document_id"}
    assert "active_qualifiers" not in properties
    assert "excluded_qualifiers" not in properties
    description = tool["description"].casefold()
    assert "non-x" in description
    assert "without x" in description
    assert "separate branches" in description
    assert "complete evidence set" in description


def test_selection_tool_language_is_corpus_neutral_and_routes_by_metadata():
    catalog = KnowledgeBase("corpus/tell-aster").catalog()[:2]
    tool = build_select_documents_tool(catalog, max_documents=2)
    text = str(tool).casefold()
    assert "northstar" not in text
    assert "regional/effective" not in text
    assert "default/normal/base" not in text
    assert "region, product, marker" not in text
    assert "explicit entity" in tool["description"].casefold()
    assert "metadata itself" in tool["description"].casefold()
    assert "question clause" in tool["description"].casefold()
    assert "another independent clause" in tool["description"].casefold()


def test_submit_answer_tool_forbids_source_labels_as_fact_values():
    tool = build_submit_answer_tool()
    description = tool["parameters"]["properties"]["answer"]["description"].casefold()
    assert "document ids" in description
    assert "source labels" in description
    assert "not substitutes for requested factual values" in description


def test_evidence_plan_need_preserves_clause_local_qualifiers():
    catalog = KnowledgeBase("corpus/northstar-corpus").catalog()[:2]
    tool = build_select_documents_tool(catalog, max_documents=2)
    description = tool["parameters"]["properties"]["evidence_plan"]["items"]["properties"]["need"]["description"].casefold()
    assert "originating clause" in description
    assert "local qualifiers" in description
    assert "another independent clause" in description
