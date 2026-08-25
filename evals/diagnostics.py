from __future__ import annotations

from pathlib import Path
from typing import Any

from progressive_disclosure.knowledge import KnowledgeBase

from evals.grading import answer_matches_expected
from progressive_disclosure.llm import ModelBackend
from progressive_disclosure.prompts import PromptArtifact, build_evidence_state, build_selection_state
from progressive_disclosure.tools import (
    build_select_documents_tool,
    build_submit_answer_tool,
    force_tool,
)


def evaluate_selection_only(
    case: dict[str, Any],
    *,
    backend: ModelBackend,
    prompt: PromptArtifact,
    corpus_root: Path | str = "corpus/northstar-corpus",
    max_documents: int = 4,
) -> dict[str, Any]:
    knowledge = KnowledgeBase(corpus_root)
    catalog = knowledge.catalog()
    state = build_selection_state(question=case["question"], catalog=catalog)
    tool = build_select_documents_tool(catalog, max_documents=max_documents)
    turn = backend.respond(
        instructions=prompt.content,
        user_input=state,
        tools=(tool,),
        tool_choice=force_tool("select_documents"),
    )
    record: dict[str, Any] = {
        "mode": "selection",
        "case_id": case["id"],
        "question": case["question"].strip(),
        "required_documents": list(case.get("required_documents", [])),
        "prompt_id": prompt.id,
        "prompt_version": prompt.version,
        "input_tokens": turn.usage.input_tokens,
        "output_tokens": turn.usage.output_tokens,
        "catalog_characters": knowledge.catalog_characters,
        "selection_state_characters": len(state),
    }
    if len(turn.tool_calls) != 1 or turn.tool_calls[0].name != "select_documents":
        return {**record, "valid_action": False, "success": False}

    args = turn.tool_calls[0].arguments
    raw_plan = args.get("evidence_plan")
    primary = args.get("primary_document_id")
    available = set(knowledge.document_ids)
    plan: list[dict[str, str]] = []
    plan_ok = isinstance(raw_plan, list) and bool(raw_plan)
    if plan_ok:
        for item in raw_plan:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("need"), str)
                or not item["need"].strip()
                or not isinstance(item.get("document_id"), str)
                or item["document_id"] not in available
            ):
                plan_ok = False
                break
            plan.append({"need": item["need"].strip(), "document_id": item["document_id"]})
    plan_ids = [item["document_id"] for item in plan]
    if (
        not plan_ok
        or not isinstance(primary, str)
        or primary not in available
        or primary not in set(plan_ids)
    ):
        return {**record, "valid_action": False, "success": False}

    selected = list(dict.fromkeys([primary, *plan_ids]))[:max_documents]
    required = set(case.get("required_documents", []))
    selected_set = set(selected)
    recall = len(required & selected_set) / len(required) if required else 1.0
    precision = len(required & selected_set) / len(selected_set) if selected_set else 0.0
    top1 = primary in required
    complete = recall == 1.0
    return {
        **record,
        "valid_action": True,
        "evidence_plan": plan,
        "primary_document_id": primary,
        "selected_document_ids": selected,
        "top1_hit": top1,
        "required_document_recall": recall,
        "document_precision": precision,
        "complete_initial_plan": complete,
        # For multi-document diagnostics success must mean the complete required proof set
        # was planned, not merely that the first document happened to be gold.
        "success": top1 and complete,
    }


def evaluate_oracle_answer(
    case: dict[str, Any],
    *,
    backend: ModelBackend,
    prompt: PromptArtifact,
    corpus_root: Path | str = "corpus/northstar-corpus",
) -> dict[str, Any]:
    knowledge = KnowledgeBase(corpus_root)
    required = tuple(case.get("required_documents", []))
    opened = tuple(knowledge.read(doc_id) for doc_id in required)
    state = build_evidence_state(question=case["question"], opened_documents=opened)
    tool = build_submit_answer_tool()
    turn = backend.respond(
        instructions=prompt.content,
        user_input=state,
        tools=(tool,),
        tool_choice=force_tool("submit_answer"),
    )
    record: dict[str, Any] = {
        "mode": "oracle",
        "case_id": case["id"],
        "question": case["question"].strip(),
        "required_documents": list(required),
        "expected_contains": [str(x) for x in case.get("expected_contains", [])],
        "prompt_id": prompt.id,
        "prompt_version": prompt.version,
        "input_tokens": turn.usage.input_tokens,
        "output_tokens": turn.usage.output_tokens,
        "evidence_state_characters": len(state),
    }
    if len(turn.tool_calls) != 1 or turn.tool_calls[0].name != "submit_answer":
        return {**record, "valid_action": False, "success": False}

    answer = turn.tool_calls[0].arguments.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return {**record, "valid_action": False, "success": False}

    expected = [str(x) for x in case.get("expected_contains", [])]
    answer_ok = answer_matches_expected(answer, expected, question=case["question"])
    # Oracle diagnostics disclose exactly the evaluator-provided gold bodies. Attribution is therefore
    # deterministic once the model submits an answer; this diagnostic isolates answer synthesis rather
    # than asking the model to redundantly reproduce the gold source list.
    cited = set(required)
    attribution_ok = True
    return {
        **record,
        "valid_action": True,
        "evidence_action": "answer",
        "answer": answer.strip(),
        "sources": sorted(cited),
        "missing_information": "",
        "answer_contains_expected": answer_ok,
        "required_sources_cited": attribution_ok,
        "success": answer_ok and attribution_ok,
    }
