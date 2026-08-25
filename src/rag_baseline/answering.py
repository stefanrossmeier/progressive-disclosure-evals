from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from progressive_disclosure.llm import ModelBackend, ModelUsage
from progressive_disclosure.prompts import PromptArtifact
from progressive_disclosure.tools import force_tool

from .models import RagSearchResult


@dataclass(frozen=True)
class RagAnswerResult:
    answer: str
    cited_sources: tuple[str, ...]
    termination: str
    model_turns: int
    tool_calls: int
    usage: ModelUsage


def _answer_tool(document_ids: tuple[str, ...]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": "submit_rag_answer",
        "description": "Submit the answer grounded only in the retrieved evidence excerpts.",
        "strict": True,
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "Complete user-facing answer supported by the retrieved excerpts.",
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(document_ids)},
                    "description": (
                        "Document IDs whose retrieved excerpts support the answer. Duplicate IDs are tolerated by "
                        "the schema and de-duplicated by the client because OpenAI strict function schemas support "
                        "only a subset of JSON Schema array constraints."
                    ),
                },
            },
            "required": ["answer", "sources"],
        },
    }


def build_rag_answer_state(question: str, results: list[RagSearchResult]) -> str:
    lines = ["QUESTION", question.strip(), "", "RETRIEVED EVIDENCE EXCERPTS"]
    for result in results:
        chunk = result.chunk
        lines.extend(
            [
                "",
                f"### Rank {result.rank} | {chunk.document_id} | {chunk.title}",
                f"Path: {chunk.path}",
            ]
        )
        if chunk.heading:
            lines.append(f"Section: {chunk.heading}")
        lines.append(chunk.text.strip())
    lines.extend(
        [
            "",
            "Answer only from these retrieved excerpts. Cite only document IDs represented above.",
        ]
    )
    return "\n".join(lines)


class RagAnswerer:
    def __init__(
        self,
        backend: ModelBackend,
        *,
        prompt: PromptArtifact,
        max_protocol_retries: int = 1,
    ):
        self.backend = backend
        self.prompt = prompt
        self.max_protocol_retries = max_protocol_retries

    def answer(self, question: str, results: list[RagSearchResult]) -> RagAnswerResult:
        if not results:
            return RagAnswerResult(
                answer="",
                cited_sources=(),
                termination="no_retrieval_results",
                model_turns=0,
                tool_calls=0,
                usage=ModelUsage(),
            )
        document_ids = tuple(dict.fromkeys(result.chunk.document_id for result in results))
        tool = _answer_tool(document_ids)
        state = build_rag_answer_state(question, results)
        usage = ModelUsage()
        model_turns = 0
        tool_calls = 0
        error = ""
        for attempt in range(self.max_protocol_retries + 1):
            model_turns += 1
            user_input = state
            if error:
                user_input += (
                    "\n\nPROTOCOL CORRECTION\n"
                    f"The previous response was invalid: {error}\n"
                    "Call submit_rag_answer exactly once with a non-empty answer and valid sources."
                )
            turn = self.backend.respond(
                instructions=self.prompt.content,
                user_input=user_input,
                tools=[tool],
                tool_choice=force_tool("submit_rag_answer"),
            )
            usage = usage + turn.usage
            tool_calls += len(turn.tool_calls)
            if len(turn.tool_calls) != 1:
                error = f"expected exactly one tool call, received {len(turn.tool_calls)}"
                continue
            call = turn.tool_calls[0]
            if call.name != "submit_rag_answer":
                error = f"expected submit_rag_answer, received {call.name}"
                continue
            answer = call.arguments.get("answer")
            sources = call.arguments.get("sources")
            if not isinstance(answer, str) or not answer.strip():
                error = "answer must be a non-empty string"
                continue
            if not isinstance(sources, list) or not all(isinstance(x, str) for x in sources):
                error = "sources must be a list of document IDs"
                continue
            invalid_sources = [source for source in sources if source not in document_ids]
            if invalid_sources:
                error = f"sources include documents that were not retrieved: {invalid_sources}"
                continue
            return RagAnswerResult(
                answer=answer.strip(),
                cited_sources=tuple(dict.fromkeys(sources)),
                termination="answer",
                model_turns=model_turns,
                tool_calls=tool_calls,
                usage=usage,
            )
        return RagAnswerResult(
            answer="",
            cited_sources=(),
            termination="protocol_failure",
            model_turns=model_turns,
            tool_calls=tool_calls,
            usage=usage,
        )
