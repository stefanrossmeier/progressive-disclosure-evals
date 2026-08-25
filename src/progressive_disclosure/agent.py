from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .knowledge import KnowledgeBase
from .llm import ModelBackend, ModelUsage
from .models import KnowledgeDocument
from .prompts import (
    PromptArtifact,
    build_evidence_state,
    build_selection_state,
    load_prompt_artifact,
)
from .tools import (
    build_request_more_evidence_tool,
    build_select_documents_tool,
    build_submit_answer_tool,
    force_tool,
)


@dataclass(frozen=True)
class AgentEvent:
    turn: int
    kind: str
    data: dict[str, Any]


@dataclass(frozen=True)
class AgentResult:
    answer: str
    termination: str
    model_turns: int
    tool_calls: int
    document_reads: int
    answer_attempts: int
    usage: ModelUsage
    events: tuple[AgentEvent, ...]
    prompt_id: str
    prompt_version: int
    cited_sources: tuple[str, ...] = ()
    opened_document_ids: tuple[str, ...] = ()
    selection_rounds: int = 0


class ProgressiveDisclosureAgent:
    """Complete metadata evidence plan -> body disclosure -> evidence resolution.

    The first model call maps atomic answer obligations to the smallest complete set
    of document bodies it expects to need. Those bodies are disclosed together and a
    second call resolves the answer. Recovery selections are bounded and available only for a concrete missing obligation.
    The configured round limit keeps single-document work on the reliable two-call path
    when the first plan is sufficient while allowing targeted progressive discovery when it is not.
    """

    def __init__(
        self,
        backend: ModelBackend,
        *,
        max_documents: int = 4,
        max_selection_rounds: int = 2,
        max_protocol_retries: int = 1,
        prompt: PromptArtifact | None = None,
        instructions: str | None = None,
    ):
        if max_documents < 1:
            raise ValueError("max_documents must be >= 1")
        if max_selection_rounds < 1:
            raise ValueError("max_selection_rounds must be >= 1")
        if max_protocol_retries < 0:
            raise ValueError("max_protocol_retries must be >= 0")
        if prompt is not None and instructions is not None:
            raise ValueError("provide either prompt or instructions, not both")
        self.backend = backend
        self.max_documents = max_documents
        self.max_selection_rounds = max_selection_rounds
        self.max_protocol_retries = max_protocol_retries
        if prompt is None:
            prompt = (
                load_prompt_artifact()
                if instructions is None
                else PromptArtifact(
                    id="inline",
                    version=0,
                    role="system",
                    path=Path("<inline>"),
                    content=instructions,
                )
            )
        self.prompt = prompt
        self.instructions = prompt.content

    def run(self, question: str, knowledge: KnowledgeBase) -> AgentResult:
        if not question.strip():
            raise ValueError("question must not be empty")

        catalog = knowledge.catalog()
        opened: dict[str, KnowledgeDocument] = {}
        read_order: list[str] = []
        events: list[AgentEvent] = []
        usage = ModelUsage()
        model_turns = 0
        tool_calls = 0
        answer_attempts = 0
        selection_rounds = 0
        missing_information: str | None = None
        evidence_plan: list[tuple[str, str]] = []

        while True:
            if not opened or missing_information is not None:
                if selection_rounds >= self.max_selection_rounds:
                    return self._result(
                        answer="",
                        termination="selection_round_limit",
                        model_turns=model_turns,
                        tool_calls=tool_calls,
                        answer_attempts=answer_attempts,
                        usage=usage,
                        events=events,
                        opened_ids=read_order,
                        selection_rounds=selection_rounds,
                    )

                remaining_budget = self.max_documents - len(read_order)
                available = tuple(item for item in catalog if item.id not in opened)
                if remaining_budget <= 0 or not available:
                    return self._result(
                        answer="",
                        termination="document_limit",
                        model_turns=model_turns,
                        tool_calls=tool_calls,
                        answer_attempts=answer_attempts,
                        usage=usage,
                        events=events,
                        opened_ids=read_order,
                        selection_rounds=selection_rounds,
                    )

                selection_rounds += 1
                discovered_references = tuple(dict.fromkeys(
                    ref
                    for doc_id in read_order
                    for ref in opened[doc_id].references
                    if ref not in opened and any(item.id == ref for item in available)
                ))
                state = build_selection_state(
                    question=question,
                    catalog=available,
                    already_opened=tuple(read_order),
                    missing_information=missing_information,
                    discovered_references=discovered_references,
                )
                tool = build_select_documents_tool(
                    available,
                    max_documents=remaining_budget,
                )
                available_ids = {item.id for item in available}
                selection_args: tuple[list[tuple[str, str]], str] | None = None
                for protocol_attempt in range(self.max_protocol_retries + 1):
                    model_turns += 1
                    turn = self.backend.respond(
                        instructions=self.instructions,
                        user_input=state,
                        tools=(tool,),
                        tool_choice=force_tool("select_documents"),
                    )
                    usage = usage + turn.usage
                    events.append(
                        AgentEvent(
                            turn=model_turns,
                            kind="model_turn",
                            data={
                                "stage": "selection",
                                "selection_round": selection_rounds,
                                "protocol_attempt": protocol_attempt + 1,
                                "opened_documents": list(read_order),
                                "available_document_count": len(available),
                                "state_characters": len(state),
                                "tool_call_count": len(turn.tool_calls),
                            },
                        )
                    )
                    error = ""
                    if len(turn.tool_calls) != 1 or turn.tool_calls[0].name != "select_documents":
                        error = "expected_exactly_one_select_documents_call"
                    else:
                        tool_calls += 1
                        args = turn.tool_calls[0].arguments
                        raw_plan = args.get("evidence_plan")
                        primary = args.get("primary_document_id")
                        parsed_plan: list[tuple[str, str]] = []
                        plan_ok = isinstance(raw_plan, list) and bool(raw_plan)
                        if plan_ok:
                            for item in raw_plan:
                                if (
                                    not isinstance(item, dict)
                                    or not isinstance(item.get("need"), str)
                                    or not item["need"].strip()
                                    or not isinstance(item.get("document_id"), str)
                                    or item["document_id"] not in available_ids
                                ):
                                    plan_ok = False
                                    break
                                parsed_plan.append((item["need"].strip(), item["document_id"]))
                        plan_ids = {document_id for _, document_id in parsed_plan}
                        if (
                            isinstance(primary, str)
                            and primary in available_ids
                            and plan_ok
                            and primary in plan_ids
                        ):
                            selection_args = (parsed_plan, primary)
                            break
                        error = "invalid_select_documents_arguments"

                    events.append(
                        AgentEvent(
                            turn=model_turns,
                            kind="invalid_model_action",
                            data={
                                "stage": "selection",
                                "error": error,
                                "protocol_attempt": protocol_attempt + 1,
                                "text": turn.text,
                                "tool_calls": [
                                    {"name": call.name, "arguments": call.arguments}
                                    for call in turn.tool_calls
                                ],
                            },
                        )
                    )
                    if protocol_attempt < self.max_protocol_retries:
                        events.append(
                            AgentEvent(
                                turn=model_turns,
                                kind="protocol_retry",
                                data={"stage": "selection", "reason": error},
                            )
                        )

                if selection_args is None:
                    return self._result(
                        answer="",
                        termination="invalid_model_action",
                        model_turns=model_turns,
                        tool_calls=tool_calls,
                        answer_attempts=answer_attempts,
                        usage=usage,
                        events=events,
                        opened_ids=read_order,
                        selection_rounds=selection_rounds,
                    )

                round_plan, primary = selection_args

                planned_ids = [document_id for _, document_id in round_plan]
                selected = list(dict.fromkeys([primary, *planned_ids]))
                truncated = len(selected) > remaining_budget
                selected = selected[:remaining_budget]
                selected_set = set(selected)
                disclosed_round_plan = [
                    (need, document_id)
                    for need, document_id in round_plan
                    if document_id in selected_set
                ]
                for obligation in disclosed_round_plan:
                    if obligation not in evidence_plan:
                        evidence_plan.append(obligation)
                events.append(
                    AgentEvent(
                        turn=model_turns,
                        kind="select_documents",
                        data={
                            "selection_round": selection_rounds,
                            "evidence_plan": [
                                {"need": need, "document_id": document_id}
                                for need, document_id in disclosed_round_plan
                            ],
                            "primary_document_id": primary,
                            "selected_document_ids": selected,
                            "selection_truncated": truncated,
                            "missing_information": missing_information or "",
                        },
                    )
                )
                for document_id in selected:
                    document = knowledge.read(document_id)
                    opened[document_id] = document
                    read_order.append(document_id)
                    events.append(
                        AgentEvent(
                            turn=model_turns,
                            kind="read_document",
                            data={
                                "document_id": document_id,
                                "content_characters": len(document.content),
                                "references": list(document.references),
                            },
                        )
                    )
                missing_information = None

            state = build_evidence_state(
                question=question,
                opened_documents=tuple(opened[doc_id] for doc_id in read_order),
                evidence_plan=tuple(evidence_plan),
            )
            submit_tool = build_submit_answer_tool()
            request_more_tool = build_request_more_evidence_tool()
            evidence_action: tuple[str, str, str] | None = None
            repair_instruction = ""
            for protocol_attempt in range(self.max_protocol_retries + 1):
                model_turns += 1
                request_state = state
                if repair_instruction:
                    request_state = (
                        f"{state}\n\nPROTOCOL REPAIR\n{repair_instruction}\n"
                        "Make exactly one valid tool call. If the disclosed evidence is sufficient, "
                        "call submit_answer with the complete non-empty final answer. Otherwise call "
                        "request_more_evidence with one precise non-empty missing fact."
                    )
                turn = self.backend.respond(
                    instructions=self.instructions,
                    user_input=request_state,
                    tools=(submit_tool, request_more_tool),
                    tool_choice="required",
                )
                usage = usage + turn.usage
                events.append(
                    AgentEvent(
                        turn=model_turns,
                        kind="model_turn",
                        data={
                            "stage": "evidence",
                            "protocol_attempt": protocol_attempt + 1,
                            "opened_documents": list(read_order),
                            "state_characters": len(request_state),
                            "tool_call_count": len(turn.tool_calls),
                        },
                    )
                )

                error = ""
                if len(turn.tool_calls) != 1:
                    error = "expected_exactly_one_evidence_action"
                    repair_instruction = (
                        "The previous evidence response did not contain exactly one evidence-action tool call."
                    )
                else:
                    tool_calls += 1
                    answer_attempts += 1
                    call = turn.tool_calls[0]
                    args = call.arguments
                    if call.name == "submit_answer":
                        answer = args.get("answer")
                        if isinstance(answer, str) and answer.strip():
                            evidence_action = ("answer", answer.strip(), "")
                            break
                        error = "submit_answer_requires_non_empty_answer"
                        repair_instruction = (
                            "The previous submit_answer call chose the correct completion action but its "
                            "answer field was empty. Supply the actual complete user-facing answer text."
                        )
                    elif call.name == "request_more_evidence":
                        missing = args.get("missing_information")
                        if isinstance(missing, str) and missing.strip():
                            evidence_action = ("need_more", "", missing.strip())
                            break
                        error = "request_more_evidence_requires_non_empty_missing_information"
                        repair_instruction = (
                            "The previous request_more_evidence call did not name a concrete missing fact. "
                            "Provide one precise unresolved evidence need."
                        )
                    else:
                        error = "unexpected_evidence_action_tool"
                        repair_instruction = (
                            f"The previous tool '{call.name}' is not a valid evidence action for this stage."
                        )

                events.append(
                    AgentEvent(
                        turn=model_turns,
                        kind="invalid_model_action",
                        data={
                            "stage": "evidence",
                            "error": error,
                            "protocol_attempt": protocol_attempt + 1,
                            "text": turn.text,
                            "tool_calls": [
                                {"name": call.name, "arguments": call.arguments}
                                for call in turn.tool_calls
                            ],
                        },
                    )
                )
                if protocol_attempt < self.max_protocol_retries:
                    events.append(
                        AgentEvent(
                            turn=model_turns,
                            kind="protocol_retry",
                            data={"stage": "evidence", "reason": error},
                        )
                    )

            if evidence_action is None:
                return self._result(
                    answer="",
                    termination="invalid_model_action",
                    model_turns=model_turns,
                    tool_calls=tool_calls,
                    answer_attempts=answer_attempts,
                    usage=usage,
                    events=events,
                    opened_ids=read_order,
                    selection_rounds=selection_rounds,
                )

            status, answer, missing = evidence_action
            if status == "answer":
                # Every document in evidence_plan was selected by the model as material to a concrete
                # obligation. Once the resolver confirms that the complete plan is established, carry
                # those planned bodies into attribution deterministically. This avoids losing a premise
                # solely because the final structured call omitted it from its source array.
                planned_sources = [document_id for _, document_id in evidence_plan]
                cited = tuple(dict.fromkeys(planned_sources))
                events.append(
                    AgentEvent(
                        turn=model_turns,
                        kind="submit_answer",
                        data={"sources": list(cited)},
                    )
                )
                return self._result(
                    answer=answer,
                    termination="answer",
                    model_turns=model_turns,
                    tool_calls=tool_calls,
                    answer_attempts=answer_attempts,
                    usage=usage,
                    events=events,
                    opened_ids=read_order,
                    cited_sources=cited,
                    selection_rounds=selection_rounds,
                )

            events.append(
                AgentEvent(
                    turn=model_turns,
                    kind="need_more_evidence",
                    data={"missing_information": missing},
                )
            )
            missing_information = missing

    def _result(
        self,
        *,
        answer: str,
        termination: str,
        model_turns: int,
        tool_calls: int,
        answer_attempts: int,
        usage: ModelUsage,
        events: list[AgentEvent],
        opened_ids: list[str],
        selection_rounds: int,
        cited_sources: tuple[str, ...] = (),
    ) -> AgentResult:
        return AgentResult(
            answer=answer,
            termination=termination,
            model_turns=model_turns,
            tool_calls=tool_calls,
            document_reads=len(opened_ids),
            answer_attempts=answer_attempts,
            usage=usage,
            events=tuple(events),
            prompt_id=self.prompt.id,
            prompt_version=self.prompt.version,
            cited_sources=cited_sources,
            opened_document_ids=tuple(opened_ids),
            selection_rounds=selection_rounds,
        )
