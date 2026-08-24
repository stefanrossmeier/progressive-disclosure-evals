import pytest

from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.tools import (
    build_request_more_evidence_tool,
    build_select_documents_tool,
    build_submit_answer_tool,
    force_tool,
)


def test_select_documents_tool_is_strict_and_enumerates_available_documents():
    catalog = KnowledgeBase("corpus/northstar").catalog()[:2]
    tool = build_select_documents_tool(catalog, max_documents=2)
    assert tool["name"] == "select_documents"
    assert tool["strict"] is True
    active = tool["parameters"]["properties"]["active_qualifiers"]
    excluded = tool["parameters"]["properties"]["excluded_qualifiers"]
    primary = tool["parameters"]["properties"]["primary_document_id"]
    evidence_plan = tool["parameters"]["properties"]["evidence_plan"]
    assert active["items"]["type"] == "string"
    assert excluded["items"]["type"] == "string"
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


def test_select_documents_tool_requires_active_and_excluded_qualifier_bookkeeping():
    catalog = KnowledgeBase("corpus/northstar").catalog()[:2]
    tool = build_select_documents_tool(catalog, max_documents=2)
    required = tool["parameters"]["required"]
    assert "active_qualifiers" in required
    assert "excluded_qualifiers" in required
    assert "evidence_plan" in required
    assert "complete evidence set" in tool["description"].lower()
