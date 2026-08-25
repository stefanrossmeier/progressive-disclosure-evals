from __future__ import annotations

from progressive_disclosure.agent import ProgressiveDisclosureAgent
from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.llm import ModelTurn, ModelUsage, ToolCall


class ScriptedBackend:
    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = []

    def respond(self, **kwargs):
        self.calls.append(kwargs)
        if not self.turns:
            raise AssertionError("scripted backend exhausted")
        return self.turns.pop(0)


def select_call(i, primary, additional=(), usage=ModelUsage(), needs=()):
    return ModelTurn(
        response_id=f"r{i}",
        text="",
        tool_calls=(ToolCall(
            f"c{i}",
            "select_documents",
            {
                "evidence_plan": [
                    {
                        "need": (
                            needs[index - 1]
                            if index <= len(needs)
                            else f"need-{index}"
                        ),
                        "document_id": document_id,
                    }
                    for index, document_id in enumerate([primary, *additional], start=1)
                ],
                "primary_document_id": primary,
            },
        ),),
        usage=usage,
    )


def answer_call(i, answer, sources=(), usage=ModelUsage()):
    return ModelTurn(
        response_id=f"r{i}",
        text="",
        tool_calls=(ToolCall(
            f"c{i}",
            "submit_answer",
            {"answer": answer},
        ),),
        usage=usage,
    )


def need_more_call(i, missing):
    return ModelTurn(
        response_id=f"r{i}",
        text="",
        tool_calls=(ToolCall(
            f"c{i}",
            "request_more_evidence",
            {"missing_information": missing},
        ),),
    )


def test_ideal_single_document_case_is_selection_plus_answer():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.credits.migration"),
        answer_call(2, "Team VIOLET using SABLE-88.", ["commercial.billing.credits.migration"]),
    ])
    result = ProgressiveDisclosureAgent(backend).run("What applies to MIG-2?", KnowledgeBase("corpus/northstar-corpus"))
    assert result.termination == "answer"
    assert result.model_turns == 2
    assert result.document_reads == 1
    assert result.selection_rounds == 1
    assert result.cited_sources == ("commercial.billing.credits.migration",)


def test_first_call_sees_activation_catalog_and_only_selection_tool():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.credits.migration"),
        answer_call(2, "VIOLET SABLE-88", ["commercial.billing.credits.migration"]),
    ])
    ProgressiveDisclosureAgent(backend, max_documents=1).run("MIG-2?", KnowledgeBase("corpus/northstar-corpus"))
    first = backend.calls[0]
    assert [tool["name"] for tool in first["tools"]] == ["select_documents"]
    assert first["tool_choice"] == {"type": "function", "name": "select_documents"}
    assert "commercial.billing.credits.migration" in first["user_input"]
    assert "MIG-2" in first["user_input"]
    assert "SABLE-88" not in first["user_input"]


def test_after_selection_model_sees_body_but_not_full_catalog():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.credits.migration"),
        answer_call(2, "VIOLET SABLE-88", ["commercial.billing.credits.migration"]),
    ])
    ProgressiveDisclosureAgent(backend).run("MIG-2?", KnowledgeBase("corpus/northstar-corpus"))
    second = backend.calls[1]
    assert [tool["name"] for tool in second["tools"]] == ["submit_answer", "request_more_evidence"]
    assert second["tool_choice"] == "required"
    assert "SABLE-88" in second["user_input"]
    assert "AVAILABLE DOCUMENT METADATA" not in second["user_input"]


def test_multiple_documents_can_be_selected_in_one_discovery_call():
    backend = ScriptedBackend([
        select_call(
            1,
            "governance.security.credentials.emergency-access",
            ["operations.maintenance.emergency.authorization"],
        ),
        answer_call(2, "combined", [
            "governance.security.credentials.emergency-access",
            "operations.maintenance.emergency.authorization",
        ]),
    ])
    result = ProgressiveDisclosureAgent(backend).run("Need both policies", KnowledgeBase("corpus/northstar-corpus"))
    assert result.document_reads == 2
    assert result.model_turns == 2
    assert result.opened_document_ids[0] == "governance.security.credentials.emergency-access"


def test_bounded_recovery_selection_is_available_only_after_declared_gap():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.refunds.standard"),
        need_more_call(2, "Need the D-8 duplicate-billing exception authority."),
        select_call(3, "commercial.billing.refunds.exceptions"),
        answer_call(4, "PEBBLE GLASS-12", ["commercial.billing.refunds.exceptions"]),
    ])
    result = ProgressiveDisclosureAgent(backend).run("D-8 refund", KnowledgeBase("corpus/northstar-corpus"))
    assert result.termination == "answer"
    assert result.selection_rounds == 2
    assert result.opened_document_ids == (
        "commercial.billing.refunds.standard",
        "commercial.billing.refunds.exceptions",
    )
    third = backend.calls[2]["user_input"]
    assert "UNRESOLVED EVIDENCE NEED" in third
    assert "commercial.billing.refunds.standard" not in [
        x for x in backend.calls[2]["tools"][0]["parameters"]["properties"]["primary_document_id"]["enum"]
    ]


def test_document_budget_stops_recovery_after_evidence_gap():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.refunds.standard"),
        need_more_call(2, "Need the exception."),
    ])
    result = ProgressiveDisclosureAgent(backend, max_documents=1).run("D-8 refund", KnowledgeBase("corpus/northstar-corpus"))
    assert result.termination == "document_limit"
    assert result.model_turns == 2


def test_usage_accumulates_across_stateless_stage_calls():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.credits.migration", usage=ModelUsage(100, 5)),
        answer_call(2, "ok", ["commercial.billing.credits.migration"], usage=ModelUsage(200, 7)),
    ])
    result = ProgressiveDisclosureAgent(backend).run("MIG-2?", KnowledgeBase("corpus/northstar-corpus"))
    assert result.usage.input_tokens == 300
    assert result.usage.output_tokens == 12


def test_invalid_or_missing_tool_call_terminates_cleanly():
    backend = ScriptedBackend([ModelTurn("r1", "", ()), ModelTurn("r2", "", ())])
    result = ProgressiveDisclosureAgent(backend).run("q", KnowledgeBase("corpus/northstar-corpus"))
    assert result.termination == "invalid_model_action"


def test_selection_event_keeps_scope_inside_evidence_obligations():
    backend = ScriptedBackend([
        select_call(
            1,
            "governance.regions.us.billing-overrides",
            needs=("US-governed standard refund with no D-8 exception",),
        ),
        answer_call(2, "FALCON RIDGE-91", ["governance.regions.us.billing-overrides"]),
    ])
    result = ProgressiveDisclosureAgent(backend).run(
        "US-governed standard refund; no D-8 exception applies.",
        KnowledgeBase("corpus/northstar-corpus"),
    )
    selection = next(event for event in result.events if event.kind == "select_documents")
    assert "active_qualifiers" not in selection.data
    assert "excluded_qualifiers" not in selection.data
    assert selection.data["evidence_plan"][0]["need"] == "US-governed standard refund with no D-8 exception"
    assert selection.data["evidence_plan"][0]["document_id"] == "governance.regions.us.billing-overrides"


def test_evidence_call_receives_structured_routing_plan():
    backend = ScriptedBackend([
        select_call(
            1,
            "platform.products.zephyr.limits",
            ["platform.infrastructure.compute.quotas", "governance.regions.eu.data-handling"],
        ),
        answer_call(2, "Crown 613", [
            "platform.products.zephyr.limits",
            "platform.infrastructure.compute.quotas",
            "governance.regions.eu.data-handling",
        ]),
    ])
    ProgressiveDisclosureAgent(backend).run(
        "For an EU-governed Zephyr tenant, what tier remains assigned and what ceiling applies?",
        KnowledgeBase("corpus/northstar-corpus"),
    )
    evidence_state = backend.calls[1]["user_input"]
    assert "EVIDENCE OBLIGATIONS FROM ROUTING PLAN" in evidence_state
    assert "platform.products.zephyr.limits" in evidence_state
    assert "platform.infrastructure.compute.quotas" in evidence_state
    assert "governance.regions.eu.data-handling" in evidence_state


def test_one_stateless_protocol_retry_recovers_malformed_evidence_action():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.credits.migration"),
        ModelTurn("r2", "malformed", ()),
        answer_call(3, "VIOLET SABLE-88", ["commercial.billing.credits.migration"]),
    ])
    result = ProgressiveDisclosureAgent(backend).run(
        "What applies to MIG-2?", KnowledgeBase("corpus/northstar-corpus")
    )
    assert result.termination == "answer"
    assert result.model_turns == 3
    assert any(event.kind == "protocol_retry" for event in result.events)


def test_answer_citations_include_all_documents_from_completed_evidence_plan():
    backend = ScriptedBackend([
        select_call(
            1,
            "platform.products.nova.limits",
            ["platform.infrastructure.compute.quotas", "governance.regions.us.data-handling"],
        ),
        # The final model accidentally omits two planned premise sources.
        answer_call(2, "N2 Reed 137 113", ["governance.regions.us.data-handling"]),
    ])
    result = ProgressiveDisclosureAgent(backend).run(
        "For a US-governed Nova tenant, give service class, tier, normal quota, and US ceiling.",
        KnowledgeBase("corpus/northstar-corpus"),
    )
    assert result.termination == "answer"
    assert set(result.cited_sources) == {
        "platform.products.nova.limits",
        "platform.infrastructure.compute.quotas",
        "governance.regions.us.data-handling",
    }


def test_request_more_evidence_uses_precise_gap_without_protocol_failure():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.refunds.standard"),
        need_more_call(2, "Need the D-8 exception authority."),
        select_call(3, "commercial.billing.refunds.exceptions"),
        answer_call(4, "PEBBLE GLASS-12"),
    ])
    result = ProgressiveDisclosureAgent(backend).run("D-8 refund", KnowledgeBase("corpus/northstar-corpus"))
    assert result.termination == "answer"
    assert result.selection_rounds == 2


def test_empty_submit_answer_retry_receives_explicit_repair_instruction():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.credits.migration"),
        ModelTurn("r2", "", (ToolCall("c2", "submit_answer", {"answer": ""}),)),
        answer_call(3, "VIOLET SABLE-88"),
    ])
    result = ProgressiveDisclosureAgent(backend).run(
        "What applies to MIG-2?", KnowledgeBase("corpus/northstar-corpus")
    )
    assert result.termination == "answer"
    assert result.model_turns == 3
    assert "PROTOCOL REPAIR" in backend.calls[2]["user_input"]
    assert "answer field was empty" in backend.calls[2]["user_input"]


def test_v18_style_budget_can_use_two_targeted_recovery_rounds():
    backend = ScriptedBackend([
        select_call(1, "commercial.billing.refunds.standard"),
        need_more_call(2, "Need the duplicate-billing exception authority."),
        select_call(3, "commercial.billing.refunds.exceptions"),
        need_more_call(4, "Need the US billing override for the remaining scoped value."),
        select_call(5, "governance.regions.us.billing-overrides"),
        answer_call(6, "complete"),
    ])
    result = ProgressiveDisclosureAgent(
        backend,
        max_documents=4,
        max_selection_rounds=3,
    ).run("Resolve the scoped billing facts.", KnowledgeBase("corpus/northstar-corpus"))
    assert result.termination == "answer"
    assert result.selection_rounds == 3
    assert result.document_reads == 3
    assert result.model_turns == 6
