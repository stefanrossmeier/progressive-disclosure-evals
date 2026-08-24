from progressive_disclosure.llm import ModelTurn, ToolCall
from evals.agent_dev import evaluate_case, load_dev_cases


class ScriptedBackend:
    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = []

    def respond(self, **kwargs):
        self.calls.append(kwargs)
        return self.turns.pop(0)


def select(i, primary, additional=()):
    return ModelTurn(
        f"r{i}",
        "",
        (ToolCall(
            f"c{i}",
            "select_documents",
            {
                "active_qualifiers": ["subject"],
                "excluded_qualifiers": [],
                "evidence_plan": [
                    {"need": f"need-{index}", "document_id": document_id}
                    for index, document_id in enumerate([primary, *additional], start=1)
                ],
                "primary_document_id": primary,
            },
        ),),
    )


def submit(i, answer, sources=()):
    return ModelTurn(
        f"r{i}",
        "",
        (ToolCall(
            f"c{i}",
            "submit_answer",
            {"answer": answer},
        ),),
    )


def ideal_single():
    return [
        select(1, "commercial.billing.credits.migration"),
        submit(2, "Team VIOLET; code SABLE-88.", ["commercial.billing.credits.migration"]),
    ]


def test_dataset_has_five_cases_and_no_tree_gold_nodes():
    cases = load_dev_cases()
    assert len(cases) == 5
    for case in cases:
        assert case["required_documents"]
        assert "gold_nodes" not in case


def test_ideal_single_document_eval_succeeds_in_two_calls():
    case = load_dev_cases()[0]
    result = evaluate_case(case, backend=ScriptedBackend(ideal_single()))
    assert result.overall_success is True
    assert result.discovery.required_document_recall == 1.0
    assert result.discovery.document_precision == 1.0
    assert result.model_turns == result.eval_criteria.ideal_model_calls == 2
    assert result.prompt_version == 14
    assert result.failure_classification == "success"


def test_eval_output_exposes_question_and_criteria():
    result = evaluate_case(load_dev_cases()[0], backend=ScriptedBackend(ideal_single()))
    assert "MIG-2" in result.question
    assert result.eval_criteria.expected_answer_values == ("VIOLET", "SABLE-88")
    assert result.eval_criteria.gold_visible_to_agent is False
    assert "evaluator-only" in result.eval_criteria.discovery_rule


def test_wrong_selection_is_discovery_failure_even_if_runtime_accepts_answer():
    case = load_dev_cases()[0]
    result = evaluate_case(case, backend=ScriptedBackend([
        select(1, "governance.regions.apac.billing-overrides"),
        submit(2, "MIG-2 authority", ["governance.regions.apac.billing-overrides"]),
    ]))
    assert result.discovery.required_document_recall == 0.0
    assert result.failure_classification == "knowledge_discovery_failure"
    assert result.overall_success is False


def test_unnecessary_document_selection_reduces_precision_and_is_visible():
    case = load_dev_cases()[0]
    result = evaluate_case(case, backend=ScriptedBackend([
        select(
            1,
            "commercial.billing.credits.outage",
            ["commercial.billing.credits.migration"],
        ),
        submit(2, "VIOLET SABLE-88", ["commercial.billing.credits.migration"]),
    ]))
    assert result.overall_success is True
    assert result.discovery.document_precision == 0.5
    assert result.discovery.wrong_documents_before_first_gold == 1
    assert result.failure_classification == "success_with_discovery_inefficiency"


def test_multi_document_ideal_is_one_selection_plus_one_answer():
    case = next(c for c in load_dev_cases() if c["id"] == "DEV-AGENT-005")
    result = evaluate_case(case, backend=ScriptedBackend([
        select(
            1,
            "governance.security.credentials.emergency-access",
            ["operations.maintenance.emergency.authorization"],
        ),
        submit(2, "SABLE QUILL-39 COMET-48", [
            "governance.security.credentials.emergency-access",
            "operations.maintenance.emergency.authorization",
        ]),
    ]))
    assert result.eval_criteria.ideal_model_calls == 2
    assert result.overall_success is True


def test_context_metrics_show_only_fraction_of_leaf_content_loaded():
    result = evaluate_case(load_dev_cases()[0], backend=ScriptedBackend(ideal_single()))
    assert result.context["catalog_documents"] == 40
    assert 0 < result.context["knowledge_content_fraction_loaded"] < 0.1
    assert result.context["full_corpus_characters"] > result.context["opened_document_characters"]


def test_numeric_thousands_separator_is_not_required_for_answer_match():
    case = {
        "id": "TEST-NUMERIC",
        "question": "What ceiling applies?",
        "expected_contains": ["1,019"],
        "required_documents": ["governance.regions.apac.data-handling"],
    }
    result = evaluate_case(case, backend=ScriptedBackend([
        select(1, "governance.regions.apac.data-handling"),
        submit(2, "The ceiling is 1019 objects.", ["governance.regions.apac.data-handling"]),
    ]))
    assert result.answer_contains_expected is True


def test_eval_labels_and_expected_values_are_not_exposed_to_agent():
    case = {
        "id": "EVAL-SENTINEL",
        "title": "__EVAL_TITLE_SENTINEL__",
        "tags": ["single_doc", "__EVAL_TAG_SENTINEL__"],
        "question": "What applies to MIG-2?",
        "expected_contains": ["__EXPECTED_VALUE_SENTINEL__"],
        "required_documents": ["commercial.billing.credits.migration"],
    }
    backend = ScriptedBackend([
        select(1, "commercial.billing.credits.migration"),
        submit(2, "No sentinel values are needed here.", ["commercial.billing.credits.migration"]),
    ])

    evaluate_case(case, backend=backend)

    model_facing = "\n".join(call["user_input"] for call in backend.calls)
    instructions = "\n".join(call["instructions"] for call in backend.calls)
    combined = model_facing + "\n" + instructions
    assert "__EVAL_TITLE_SENTINEL__" not in combined
    assert "__EVAL_TAG_SENTINEL__" not in combined
    assert "__EXPECTED_VALUE_SENTINEL__" not in combined
    assert "single_doc" not in combined


def test_compact_utc_range_matches_individual_expected_timestamps():
    case = {
        "id": "TEST-TIME-RANGE",
        "question": "What is the window?",
        "expected_contains": ["04:23 UTC", "05:36 UTC"],
        "required_documents": ["operations.maintenance.scheduled.windows"],
    }
    result = evaluate_case(case, backend=ScriptedBackend([
        select(1, "operations.maintenance.scheduled.windows"),
        submit(
            2,
            "The standard window is Thursday 04:23–05:36 UTC.",
            ["operations.maintenance.scheduled.windows"],
        ),
    ]))
    assert result.answer_contains_expected is True
