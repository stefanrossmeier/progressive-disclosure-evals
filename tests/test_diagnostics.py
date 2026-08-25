from evals.diagnostics import evaluate_oracle_answer, evaluate_selection_only
from evals.benchmark import load_eval_dataset
from progressive_disclosure.llm import ModelTurn, ToolCall
from progressive_disclosure.prompts import load_prompt_artifact


class Backend:
    def __init__(self, turn):
        self.turn = turn

    def respond(self, **kwargs):
        return self.turn


def test_selection_only_reports_top1_and_recall():
    case = load_eval_dataset()["cases"][0]
    turn = ModelTurn(
        "r1",
        "",
        (ToolCall(
            "c1",
            "select_documents",
            {
                "evidence_plan": [
                    {"need": "MIG-2 approval authority", "document_id": "commercial.billing.credits.migration"}
                ],
                "primary_document_id": "commercial.billing.credits.migration",
            },
        ),),
    )
    result = evaluate_selection_only(case, backend=Backend(turn), prompt=load_prompt_artifact())
    assert result["top1_hit"] is True
    assert result["success"] is True
    assert result["selected_document_ids"] == ["commercial.billing.credits.migration"]
    assert result["evidence_plan"][0]["document_id"] == "commercial.billing.credits.migration"


def test_oracle_answer_measures_answer_ceiling_without_retrieval():
    case = load_eval_dataset()["cases"][0]
    turn = ModelTurn(
        "r1",
        "",
        (ToolCall(
            "c1",
            "submit_answer",
            {"answer": "Team VIOLET with SABLE-88."},
        ),),
    )
    result = evaluate_oracle_answer(case, backend=Backend(turn), prompt=load_prompt_artifact())
    assert result["answer_contains_expected"] is True
    assert result["required_sources_cited"] is True
    assert result["success"] is True
    assert result["evidence_action"] == "answer"
    assert "status" not in result


def test_multi_selection_success_requires_complete_initial_plan_not_only_gold_top1():
    case = {
        "id": "TEST-MULTI-DIAG",
        "question": "Need product assignment and regional ceiling.",
        "required_documents": [
            "platform.products.nova.limits",
            "governance.regions.us.data-handling",
        ],
    }
    turn = ModelTurn(
        "r1",
        "",
        (ToolCall(
            "c1",
            "select_documents",
            {
                "evidence_plan": [
                    {"need": "product assignment", "document_id": "platform.products.nova.limits"}
                ],
                "primary_document_id": "platform.products.nova.limits",
            },
        ),),
    )
    result = evaluate_selection_only(case, backend=Backend(turn), prompt=load_prompt_artifact())
    assert result["top1_hit"] is True
    assert result["required_document_recall"] == 0.5
    assert result["complete_initial_plan"] is False
    assert result["success"] is False
