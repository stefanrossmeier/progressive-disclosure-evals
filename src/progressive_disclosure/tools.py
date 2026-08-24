from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .models import DocumentSummary


def build_select_documents_tool(
    documents: Sequence[DocumentSummary],
    *,
    max_documents: int,
) -> dict[str, Any]:
    ids = [document.id for document in documents]
    if not ids:
        raise ValueError("select_documents requires at least one available document")
    if max_documents < 1:
        raise ValueError("max_documents must be >= 1")
    return {
        "type": "function",
        "name": "select_documents",
        "description": (
            "Plan and select the smallest complete evidence set needed to answer every requested output. "
            "Preserve active/excluded routing qualifiers, but treat explicit question facts (region, product, "
            "marker, level, stated prerequisite) as given rather than as facts that need documentary proof. "
            "Create evidence_plan entries mapping each atomic requested fact or genuinely necessary dependency, "
            "transformation, fallback, or precedence premise to the body expected to establish it. Select all "
            "currently predictable necessary bodies now; do not defer an obvious second or third authority to a "
            "later round. Preserve contrasts such as default/normal/base versus regional/effective/lower/actual. "
            "Do not select a body solely to re-derive a supplied fact or prove that an excluded scope is absent. "
            "The primary_document_id is the best first routing match and must also appear in the evidence plan. "
            f"Use no more than {max_documents} distinct documents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "active_qualifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Short routing qualifiers explicitly present in the question that still apply, "
                        "such as a region, product, process, marker, or policy type."
                    ),
                },
                "excluded_qualifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Short routing qualifiers explicitly negated by the question. Forms such as "
                        "non-EU, not EU, or outside EU belong here, not in active_qualifiers."
                    ),
                },
                "evidence_plan": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "need": {
                                "type": "string",
                                "description": (
                                    "The atomic fact, dependency, scope-establishment, or precedence "
                                    "premise this document must establish."
                                ),
                            },
                            "document_id": {
                                "type": "string",
                                "enum": ids,
                            },
                        },
                        "required": ["need", "document_id"],
                        "additionalProperties": False,
                    },
                    "description": (
                        "Evidence obligations mapped to the document that should establish each one. Use "
                        "separate entries for distinct requested outputs and for transformations that genuinely "
                        "require multiple authorities. Multiple obligations may map to the same document. Do not "
                        "add an obligation merely to prove a case fact already stated in the question or the "
                        "absence of an excluded scope."
                    ),
                },
                "primary_document_id": {
                    "type": "string",
                    "enum": ids,
                    "description": (
                        "The most specific first document for the still-active scope. It must occur "
                        "in evidence_plan."
                    ),
                },
            },
            "required": [
                "active_qualifiers",
                "excluded_qualifiers",
                "evidence_plan",
                "primary_document_id",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    }



def build_submit_answer_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "submit_answer",
        "description": (
            "Submit the final user-facing answer when the disclosed bodies establish every planned "
            "evidence obligation. The answer must be complete, grounded in the disclosed bodies plus "
            "explicit facts supplied by the question, and must never be empty. Do not use this tool if "
            "one concrete planned obligation is still unsupported."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": (
                        "The complete concise final answer to the user's question. This field must contain "
                        "the actual answer text and must never be empty."
                    ),
                },
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
        "strict": True,
    }


def build_request_more_evidence_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "name": "request_more_evidence",
        "description": (
            "Request one bounded recovery selection only when a concrete evidence obligation from the "
            "current plan is genuinely unsupported by the disclosed bodies. Do not use this tool to "
            "reconfirm scope, prove an excluded branch absent, or re-derive a fact already supplied by "
            "the question or established by the disclosed evidence."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "missing_information": {
                    "type": "string",
                    "description": (
                        "One precise missing fact or authority needed to complete the answer. This field "
                        "must be specific and must never be empty."
                    ),
                },
            },
            "required": ["missing_information"],
            "additionalProperties": False,
        },
        "strict": True,
    }

def force_tool(name: str) -> dict[str, str]:
    return {"type": "function", "name": name}
