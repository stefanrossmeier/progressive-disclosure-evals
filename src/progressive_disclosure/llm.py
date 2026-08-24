from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolOutput:
    """Deprecated compatibility type from the conversational implementation."""

    call_id: str
    output: dict[str, Any]


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "ModelUsage") -> "ModelUsage":
        return ModelUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
        )


@dataclass(frozen=True)
class ModelTurn:
    response_id: str | None
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: ModelUsage = ModelUsage()


class ModelBackend(Protocol):
    def respond(
        self,
        *,
        instructions: str,
        user_input: str,
        tools: Sequence[dict[str, Any]],
        tool_choice: str | dict[str, Any],
    ) -> ModelTurn: ...


class OpenAIResponsesBackend:
    """Stateless adapter around the OpenAI Responses API.

    Every agent decision is sent as a fresh request. The benchmark therefore owns
    the complete progressive-disclosure state explicitly rather than relying on a
    growing provider-side conversation or previous_response_id chain.
    """

    def __init__(
        self,
        model: str,
        client: Any | None = None,
        *,
        reasoning_effort: str = "low",
        text_verbosity: str = "low",
    ):
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise RuntimeError(
                    "OpenAI backend requires the optional 'openai' package. "
                    "Install with: pip install -r requirements.txt"
                ) from exc
            client = OpenAI()

        self.model = model
        self.client = client
        self.reasoning_effort = reasoning_effort
        self.text_verbosity = text_verbosity

    def respond(
        self,
        *,
        instructions: str,
        user_input: str,
        tools: Sequence[dict[str, Any]],
        tool_choice: str | dict[str, Any],
    ) -> ModelTurn:
        if not user_input.strip():
            raise ValueError("model request requires non-empty user_input")
        if not tools:
            raise ValueError("model request requires at least one tool")

        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=user_input,
            tools=list(tools),
            tool_choice=tool_choice,
            parallel_tool_calls=False,
            store=False,
            reasoning={"effort": self.reasoning_effort},
            text={"verbosity": self.text_verbosity},
        )

        calls: list[ToolCall] = []
        for item in response.output:
            if getattr(item, "type", None) != "function_call":
                continue
            try:
                arguments = json.loads(item.arguments)
            except json.JSONDecodeError:
                arguments = {"_invalid_json": item.arguments}
            calls.append(
                ToolCall(
                    call_id=item.call_id,
                    name=item.name,
                    arguments=arguments,
                )
            )

        usage = getattr(response, "usage", None)
        model_usage = ModelUsage(
            input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
            output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
        )
        return ModelTurn(
            response_id=response.id,
            text=response.output_text or "",
            tool_calls=tuple(calls),
            usage=model_usage,
        )
