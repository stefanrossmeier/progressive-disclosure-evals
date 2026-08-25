from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from progressive_disclosure.agent import ProgressiveDisclosureAgent
from progressive_disclosure.knowledge import KnowledgeBase
from progressive_disclosure.llm import ModelBackend
from progressive_disclosure.prompts import PromptArtifact

from evals.grading import answer_matches_expected


@dataclass(frozen=True)
class EvalCriteria:
    expected_answer_values: tuple[str, ...]
    required_documents: tuple[str, ...]
    ideal_model_calls: int
    gold_visible_to_agent: bool
    answer_rule: str
    discovery_rule: str
    source_rule: str
    overall_rule: str


@dataclass(frozen=True)
class DiscoveryMetrics:
    document_reads: int
    required_document_recall: float
    document_precision: float
    wrong_documents_before_first_gold: int
    reads_to_complete_discovery: int | None
    reads_after_complete_discovery: int | None
    complete_discovery: bool


@dataclass(frozen=True)
class DevCaseResult:
    case_id: str
    question: str
    eval_criteria: EvalCriteria
    runtime_policy: dict[str, Any]
    eval_dimensions: dict[str, Any]
    answer: str
    cited_sources: tuple[str, ...]
    opened_documents: tuple[str, ...]
    evidence_excerpts: dict[str, list[str]]
    answer_contains_expected: bool
    required_sources_cited: bool
    overall_success: bool
    failure_classification: str
    termination: str
    discovery: DiscoveryMetrics
    read_trace: list[dict[str, Any]]
    model_turns: int
    tool_calls: int
    document_reads: int
    answer_attempts: int
    selection_rounds: int
    input_tokens: int
    output_tokens: int
    prompt_id: str
    prompt_version: int
    model_calls_to_complete_discovery: int | None
    extra_model_calls_after_complete_discovery: int | None
    model_call_overhead: float
    context: dict[str, Any]


def load_dev_cases(path: Path | str = "datasets/agent-dev.yaml") -> list[dict[str, Any]]:
    value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("cases"), list):
        raise ValueError("dev dataset must contain a top-level 'cases' list")
    return value["cases"]


def _criteria(case: dict[str, Any]) -> EvalCriteria:
    required = tuple(case.get("required_documents", []))
    expected = tuple(str(value) for value in case.get("expected_contains", []))
    return EvalCriteria(
        expected_answer_values=expected,
        required_documents=required,
        ideal_model_calls=2,
        gold_visible_to_agent=False,
        answer_rule=(
            "Every expected_answer_value must match the submitted answer under deterministic "
            "surface normalization; explicit how-many questions accept the requested count alone."
        ),
        discovery_rule=(
            "All required_documents must be read. Gold documents are evaluator-only; "
            "unnecessary document reads reduce precision."
        ),
        source_rule="The submitted sources must include all required_documents for this eval case.",
        overall_rule=(
            "Answer values correct AND all required documents read AND all required "
            "documents cited."
        ),
    )


def _discovery_metrics(read_order: tuple[str, ...], required: set[str]) -> DiscoveryMetrics:
    read_set = set(read_order)
    matched = read_set & required
    recall = len(matched) / len(required) if required else 1.0
    precision = len(matched) / len(read_set) if read_set else (1.0 if not required else 0.0)

    first_gold_index = next(
        (index for index, doc_id in enumerate(read_order) if doc_id in required),
        None,
    )
    complete_at: int | None = 0 if not required else None
    seen: set[str] = set()
    for index, doc_id in enumerate(read_order, start=1):
        if doc_id in required:
            seen.add(doc_id)
        if required and seen == required:
            complete_at = index
            break

    reads_after = len(read_order) - complete_at if complete_at is not None else None
    return DiscoveryMetrics(
        document_reads=len(read_order),
        required_document_recall=recall,
        document_precision=precision,
        wrong_documents_before_first_gold=(
            first_gold_index if first_gold_index is not None else len(read_order)
        ),
        reads_to_complete_discovery=complete_at,
        reads_after_complete_discovery=reads_after,
        complete_discovery=(recall == 1.0),
    )


def _read_trace(events) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for event in events:
        if event.kind == "select_documents":
            trace.append(
                {
                    "turn": event.turn,
                    "action": "select_documents",
                    "selection_round": event.data["selection_round"],
                    "evidence_plan": event.data.get("evidence_plan", []),
                    "primary_document_id": event.data["primary_document_id"],
                    "selected_document_ids": event.data["selected_document_ids"],
                    "selection_truncated": event.data["selection_truncated"],
                    "missing_information": event.data["missing_information"],
                }
            )
        elif event.kind == "read_document":
            trace.append(
                {
                    "turn": event.turn,
                    "action": "read_document",
                    "document_id": event.data["document_id"],
                    "content_characters": event.data["content_characters"],
                    "references_observed": event.data["references"],
                }
            )
        elif event.kind == "need_more_evidence":
            trace.append(
                {
                    "turn": event.turn,
                    "action": "need_more_evidence",
                    "missing_information": event.data["missing_information"],
                }
            )
        elif event.kind == "invalid_model_action":
            trace.append(
                {
                    "turn": event.turn,
                    "action": "invalid_model_action",
                    "stage": event.data.get("stage", ""),
                    "error": event.data.get("error", ""),
                    "protocol_attempt": event.data.get("protocol_attempt"),
                    "tool_calls": event.data.get("tool_calls", []),
                    "text": event.data.get("text", ""),
                }
            )
        elif event.kind == "protocol_retry":
            trace.append(
                {
                    "turn": event.turn,
                    "action": "protocol_retry",
                    "stage": event.data.get("stage", ""),
                    "reason": event.data.get("reason", ""),
                }
            )
        elif event.kind == "submit_answer":
            trace.append(
                {
                    "turn": event.turn,
                    "action": "submit_answer",
                    "sources": event.data["sources"],
                }
            )
    return trace


def _evidence_excerpts(
    knowledge: KnowledgeBase,
    sources: tuple[str, ...],
    needles: tuple[str, ...],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    folded_needles = [needle.casefold() for needle in needles]
    for source in sources:
        if source not in knowledge:
            continue
        lines = [line.strip() for line in knowledge.read(source).content.splitlines() if line.strip()]
        matches = [
            line
            for line in lines
            if any(needle in line.casefold() for needle in folded_needles)
        ]
        if matches:
            result[source] = matches[:10]
    return result


def _failure_classification(
    *,
    answer_ok: bool,
    discovery: DiscoveryMetrics,
    required_sources_cited: bool,
    termination: str,
) -> str:
    if not discovery.complete_discovery:
        return "knowledge_discovery_failure"
    if termination != "answer":
        return "incomplete_run"
    if not required_sources_cited:
        return "evidence_attribution_failure"
    if not answer_ok:
        return "knowledge_application_failure"
    if discovery.document_precision < 1.0 or (discovery.reads_after_complete_discovery or 0) > 0:
        return "success_with_discovery_inefficiency"
    return "success"


def evaluate_case(
    case: dict[str, Any],
    *,
    backend: ModelBackend,
    corpus_root: Path | str = "corpus/northstar-corpus",
    max_documents: int = 4,
    max_selection_rounds: int = 2,
    prompt: PromptArtifact | None = None,
) -> DevCaseResult:
    knowledge = KnowledgeBase(corpus_root)
    agent = ProgressiveDisclosureAgent(
        backend,
        max_documents=max_documents,
        max_selection_rounds=max_selection_rounds,
        prompt=prompt,
    )
    result = agent.run(case["question"], knowledge)

    expected = tuple(str(value) for value in case.get("expected_contains", []))
    answer_ok = answer_matches_expected(result.answer, expected, question=case["question"])
    required_documents = set(case.get("required_documents", []))
    discovery = _discovery_metrics(result.opened_document_ids, required_documents)
    required_sources_cited = required_documents.issubset(set(result.cited_sources))
    overall_success = (
        result.termination == "answer"
        and answer_ok
        and discovery.complete_discovery
        and required_sources_cited
    )

    criteria = _criteria(case)
    complete_turn: int | None = None
    if not required_documents:
        complete_turn = 0
    else:
        seen: set[str] = set()
        for event in result.events:
            if event.kind != "read_document":
                continue
            doc_id = event.data["document_id"]
            if doc_id in required_documents:
                seen.add(doc_id)
            if seen == required_documents:
                complete_turn = event.turn
                break

    extra_calls: int | None = None
    if complete_turn is not None:
        expected_answer_call = 1 if result.termination == "answer" else 0
        extra_calls = max(0, result.model_turns - complete_turn - expected_answer_call)

    full_chars = knowledge.full_content_characters
    opened_chars = sum(len(knowledge.read(doc_id).content) for doc_id in result.opened_document_ids)
    context = {
        "catalog_documents": len(knowledge.catalog()),
        "catalog_characters": knowledge.catalog_characters,
        "opened_document_characters": opened_chars,
        "full_corpus_characters": full_chars,
        "knowledge_content_fraction_loaded": opened_chars / full_chars if full_chars else 0.0,
    }

    stopping_overexploration = (discovery.reads_after_complete_discovery or 0) > 0
    eval_dimensions = {
        "discovery": {
            "status": "complete" if discovery.complete_discovery else "incomplete",
            "required_document_recall": discovery.required_document_recall,
            "document_precision": discovery.document_precision,
            "wrong_documents_before_first_gold": discovery.wrong_documents_before_first_gold,
        },
        "stopping": {
            "status": "overexplored" if stopping_overexploration else "efficient",
            "reads_after_complete_discovery": discovery.reads_after_complete_discovery,
            "extra_model_calls_after_complete_discovery": extra_calls,
        },
        "answer": {
            "status": "correct" if answer_ok else "incorrect",
            "expected_values_present": answer_ok,
        },
        "attribution": {
            "status": "complete" if required_sources_cited else "incomplete",
            "required_sources_cited": required_sources_cited,
        },
    }

    ideal_calls = max(1, criteria.ideal_model_calls)
    return DevCaseResult(
        case_id=case["id"],
        question=case["question"].strip(),
        eval_criteria=criteria,
        runtime_policy={
            "mechanism": "explicit_metadata_selection_then_selected_document_bodies",
            "state_management": "stateless_explicit_state",
            "catalog_scope": "all_available_document_frontmatter_metadata",
            "max_documents": max_documents,
            "linked_resources": "document references remain ordinary body content; recovery selection is bounded and driven by one precise missing evidence need",
            "selection_policy": "complete_atomic_evidence_plan_then_selected_bodies",
            "custom_tree_navigation": False,
        },
        eval_dimensions=eval_dimensions,
        answer=result.answer,
        cited_sources=result.cited_sources,
        opened_documents=result.opened_document_ids,
        evidence_excerpts=_evidence_excerpts(
            knowledge,
            result.cited_sources,
            expected,
        ),
        answer_contains_expected=answer_ok,
        required_sources_cited=required_sources_cited,
        overall_success=overall_success,
        failure_classification=_failure_classification(
            answer_ok=answer_ok,
            discovery=discovery,
            required_sources_cited=required_sources_cited,
            termination=result.termination,
        ),
        termination=result.termination,
        discovery=discovery,
        read_trace=_read_trace(result.events),
        model_turns=result.model_turns,
        tool_calls=result.tool_calls,
        document_reads=result.document_reads,
        answer_attempts=result.answer_attempts,
        selection_rounds=result.selection_rounds,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        prompt_id=result.prompt_id,
        prompt_version=result.prompt_version,
        model_calls_to_complete_discovery=complete_turn,
        extra_model_calls_after_complete_discovery=extra_calls,
        model_call_overhead=result.model_turns / ideal_calls,
        context=context,
    )


def result_to_dict(result: DevCaseResult) -> dict[str, Any]:
    return asdict(result)
