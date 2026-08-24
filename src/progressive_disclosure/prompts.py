from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import DocumentSummary, KnowledgeDocument


DEFAULT_AGENT_PROMPT_PATH = Path("prompts/agent/system-v14.md")


@dataclass(frozen=True)
class PromptArtifact:
    id: str
    version: int
    role: str
    path: Path
    content: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_prompt_path(path: Path | str | None = None) -> Path:
    candidate = Path(path) if path is not None else DEFAULT_AGENT_PROMPT_PATH
    if not candidate.is_absolute():
        candidate = _project_root() / candidate
    return candidate.resolve()


def load_prompt_artifact(path: Path | str | None = None) -> PromptArtifact:
    prompt_path = resolve_prompt_path(path)
    if not prompt_path.is_file():
        raise FileNotFoundError(f"prompt artifact does not exist: {prompt_path}")

    text = prompt_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"prompt artifact is missing YAML front matter: {prompt_path}")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"prompt artifact front matter is malformed: {prompt_path}")

    metadata: Any = yaml.safe_load(parts[1])
    content = parts[2].lstrip("\r\n")
    if not isinstance(metadata, dict):
        raise ValueError(f"prompt artifact front matter must be a mapping: {prompt_path}")

    required = {"id", "version", "role"}
    missing = required - metadata.keys()
    if missing:
        raise ValueError(
            f"prompt artifact missing metadata fields {sorted(missing)}: {prompt_path}"
        )
    if not isinstance(metadata["id"], str) or not metadata["id"].strip():
        raise ValueError("prompt artifact id must be a non-empty string")
    if not isinstance(metadata["version"], int) or metadata["version"] < 1:
        raise ValueError("prompt artifact version must be an integer >= 1")
    if metadata["role"] != "system":
        raise ValueError("agent prompt artifact role must be 'system'")
    if not content.strip():
        raise ValueError("prompt artifact content must not be empty")

    return PromptArtifact(
        id=metadata["id"].strip(),
        version=metadata["version"],
        role=metadata["role"],
        path=prompt_path,
        content=content.rstrip() + "\n",
    )


def build_selection_state(
    *,
    question: str,
    catalog: tuple[DocumentSummary, ...],
    already_opened: tuple[str, ...] = (),
    missing_information: str | None = None,
) -> str:
    lines = [
        "QUESTION",
        question.strip(),
        "",
        "AVAILABLE DOCUMENT METADATA (routing information only; not factual evidence)",
    ]
    for item in catalog:
        lines.append(f"- {item.id} | {item.title} | {item.description}")

    if already_opened:
        lines.extend(["", "ALREADY DISCLOSED DOCUMENTS", ", ".join(already_opened)])
    if missing_information:
        lines.extend(["", "UNRESOLVED EVIDENCE NEED", missing_information.strip()])

    lines.extend(
        [
            "",
            "Before selecting: preserve all explicit scope qualifiers and exclusions; a negative qualifier "
            "excludes only that branch and never creates an obligation to prove the excluded branch. Treat "
            "region, product, marker, level, and other facts stated by the question as given case facts unless "
            "the question explicitly asks you to determine them. Decompose every requested output into an "
            "atomic evidence obligation and map each obligation to the body expected to establish it. Select "
            "all currently predictable necessary bodies in this first plan so the evidence stage can answer in "
            "one pass when possible. For dependency chains include each body that contributes a requested fact "
            "or transformation. For precedence/fallback include both authorities when both are needed to explain "
            "the result. Preserve contrasts such as default/normal/base versus regional/effective/lower/actual as "
            "separate outputs; do not collapse them. Do not load a body merely to re-derive a fact already given "
            "by the question or solely to confirm that an excluded scope does not apply. Select the smallest "
            "complete proof set and make its best routing match primary.",
        ]
    )
    return "\n".join(lines)


def build_evidence_state(
    *,
    question: str,
    opened_documents: tuple[KnowledgeDocument, ...],
    evidence_plan: tuple[tuple[str, str], ...] = (),
) -> str:
    lines = ["QUESTION", question.strip()]
    if evidence_plan:
        lines.extend(["", "EVIDENCE OBLIGATIONS FROM ROUTING PLAN (not factual evidence)"])
        for need, document_id in evidence_plan:
            lines.append(f"- {need} -> {document_id}")
    lines.extend(["", "DISCLOSED DOCUMENT EVIDENCE"])
    for document in opened_documents:
        lines.extend(
            [
                "",
                f"### {document.id}",
                f"Title: {document.title}",
                document.content.strip(),
            ]
        )
    lines.extend(
        [
            "",
            "Audit every planned evidence obligation and every requested output against the disclosed bodies. "
            "Treat facts explicitly supplied by the question as given inputs rather than evidence gaps. Preserve "
            "requested contrasts: if the question asks for both a default/normal/base value and a regional/effective "
            "value, report both from their respective authorities rather than substituting the effective value for "
            "the default. If every planned obligation is established, call submit_answer and put the actual complete "
            "non-empty user-facing answer in its answer field; do not request another document to reconfirm scope, "
            "absence of an excluded rule, or an already established premise. If one concrete planned obligation is "
            "unsupported, call request_more_evidence with one precise non-empty missing evidence need.",
        ]
    )
    return "\n".join(lines)
