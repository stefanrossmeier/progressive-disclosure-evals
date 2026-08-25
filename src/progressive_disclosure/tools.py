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
            "Treat facts already supplied by the question as given. Create evidence_plan entries for each atomic "
            "requested fact and each genuinely indispensable relationship or transformation needed to connect "
            "those facts. Keep scope local to each evidence_plan need: make every need self-contained and preserve "
            "the identifiers, names, locations, time references, negation, counterfactual conditions, and qualifiers "
            "of the question clause that created it. `non-X` excludes X for that obligation; `without X` means "
            "evaluate that obligation with X absent even if X applies elsewhere. Contrast words such as `instead`, "
            "`whereas`, and `rather than` separate branches. Never import an identifier, process, scope, modifier, "
            "or qualifier from another independent clause. Route from the metadata itself: prefer explicit entity "
            "anchors and stated use conditions rather than assuming a fact belongs to a particular document family. "
            "Select all currently predictable necessary bodies now. Do not select a body merely for corroboration, "
            "background, topical similarity, or to re-derive a supplied fact. The primary_document_id is the best "
            "first routing match and must also appear in the evidence plan. "
            f"Use no more than {max_documents} distinct documents."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "evidence_plan": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "need": {
                                "type": "string",
                                "description": (
                                    "A self-contained atomic requested fact or indispensable relationship/"
                                    "transformation this document must establish. Preserve the originating clause's "
                                    "identifiers, negation, counterfactual condition, and local qualifiers. Do not "
                                    "import modifiers from another independent clause."
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
                        "Evidence obligations mapped to the document that should establish each one. Scope belongs "
                        "inside each need rather than in a global qualifier list. Use separate entries for distinct "
                        "requested outputs and indispensable bridges. Multiple obligations may map to the same "
                        "document. Do not add an obligation merely for background, corroboration, or to prove a case "
                        "fact already stated in the question."
                    ),
                },
                "primary_document_id": {
                    "type": "string",
                    "enum": ids,
                    "description": (
                        "The best first metadata routing match for the current evidence plan. It must occur in "
                        "evidence_plan."
                    ),
                },
            },
            "required": ["evidence_plan", "primary_document_id"],
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
                        "the actual answer text and must never be empty. Document IDs, document titles, metadata labels, and "
                        "routing-plan mappings are source labels, not substitutes for requested factual values unless "
                        "the question explicitly asks for such a source identifier."
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
                        "One precise missing fact or indispensable relationship needed to complete the answer. "
                        "This field must be specific and must never be empty."
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
