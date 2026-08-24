from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from progressive_disclosure.llm import OpenAIResponsesBackend


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeClient:
    def __init__(self, response):
        self.responses = FakeResponses(response)


def response_with_tool_call(name="read_document", arguments=None):
    item = SimpleNamespace(
        type="function_call",
        call_id="c1",
        name=name,
        arguments=json.dumps(arguments or {"document_id": "commercial.billing.credits.migration"}),
    )
    return SimpleNamespace(
        id="r1",
        output=[item],
        output_text="",
        usage=SimpleNamespace(input_tokens=12, output_tokens=3),
    )


def test_openai_adapter_maps_function_call_and_usage():
    client = FakeClient(response_with_tool_call())
    backend = OpenAIResponsesBackend("test-model", client=client)
    turn = backend.respond(
        instructions="instructions",
        user_input="state",
        tools=({"type": "function", "name": "read_document"},),
        tool_choice={"type": "function", "name": "read_document"},
    )
    assert turn.response_id == "r1"
    assert turn.tool_calls[0].arguments == {"document_id": "commercial.billing.credits.migration"}
    assert turn.usage.input_tokens == 12

    sent = client.responses.calls[0]
    assert sent["model"] == "test-model"
    assert sent["input"] == "state"
    assert sent["store"] is False
    assert sent["parallel_tool_calls"] is False
    assert sent["tool_choice"] == {"type": "function", "name": "read_document"}
    assert "previous_response_id" not in sent
    assert sent["reasoning"] == {"effort": "low"}
    assert sent["text"] == {"verbosity": "low"}


def test_openai_adapter_supports_required_choice_between_multiple_tools():
    client = FakeClient(
        response_with_tool_call(
            "submit_answer",
            {"answer": "done", "sources": ["commercial.billing.credits.migration"]},
        )
    )
    backend = OpenAIResponsesBackend("test-model", client=client)
    turn = backend.respond(
        instructions="instructions",
        user_input="state",
        tools=(
            {"type": "function", "name": "read_document"},
            {"type": "function", "name": "submit_answer"},
        ),
        tool_choice="required",
    )
    assert turn.tool_calls[0].name == "submit_answer"
    assert client.responses.calls[0]["tool_choice"] == "required"


def test_openai_adapter_is_stateless_across_calls():
    response = SimpleNamespace(id="r2", output=[], output_text="", usage=None)
    client = FakeClient(response)
    backend = OpenAIResponsesBackend("test-model", client=client)
    backend.respond(
        instructions="i",
        user_input="state 1",
        tools=({"type": "function", "name": "read_document"},),
        tool_choice="required",
    )
    backend.respond(
        instructions="i",
        user_input="state 2",
        tools=({"type": "function", "name": "read_document"},),
        tool_choice="required",
    )
    assert client.responses.calls[0]["input"] == "state 1"
    assert client.responses.calls[1]["input"] == "state 2"
    assert all("previous_response_id" not in call for call in client.responses.calls)


def test_openai_adapter_requires_nonempty_state():
    response = SimpleNamespace(id="x", output=[], output_text="", usage=None)
    backend = OpenAIResponsesBackend("test-model", client=FakeClient(response))
    with pytest.raises(ValueError, match="user_input"):
        backend.respond(
            instructions="i",
            user_input="  ",
            tools=({"type": "function", "name": "read_document"},),
            tool_choice="required",
        )


def test_openai_adapter_requires_tools():
    response = SimpleNamespace(id="x", output=[], output_text="", usage=None)
    backend = OpenAIResponsesBackend("test-model", client=FakeClient(response))
    with pytest.raises(ValueError, match="tool"):
        backend.respond(
            instructions="i",
            user_input="state",
            tools=(),
            tool_choice="required",
        )
