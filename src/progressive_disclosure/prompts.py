from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import DocumentSummary, KnowledgeDocument


DEFAULT_AGENT_PROMPT_PATH = Path("prompts/agent/system-v18.md")


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
    discovered_references: tuple[str, ...] = (),
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
    if discovered_references:
        lines.extend([
            "",
            "REFERENCES OBSERVED IN DISCLOSED BODIES (routing hints only; not factual evidence)",
            ", ".join(discovered_references),
            "Use these only as navigation hints when their metadata matches the unresolved need; do not follow them merely because they were linked.",
        ])

    lines.extend(
        [
            "",
            "Before selecting: preserve explicit identifiers, names, locations, time references, qualifiers, and "
            "exclusions inside the atomic obligation they modify. Never flatten clause-local scope into global "
            "qualifiers. Treat `non-X` as excluding X and `without X` as asking for that obligation with X absent, "
            "even when X applies elsewhere in the case. Treat contrast words such as `instead`, `whereas`, and "
            "`rather than` as branch boundaries. Treat facts "
            "already supplied by the question as case facts unless the question asks you to determine them. Split "
            "the requested output into independent atomic evidence obligations and map each obligation to the "
            "metadata entry expected to establish it. Prefer explicit entity anchors in metadata over assumptions "
            "about which document family should contain a fact. For relational questions include every predictable "
            "indispensable bridge needed to connect an identified entity to the requested property. For compound "
            "questions, make each obligation self-contained and preserve the wording, negation, counterfactual "
            "condition, and local qualifiers of the clause that created it; do not import an identifier, process, "
            "scope, modifier, or qualifier from another independent clause. Do not "
            "select documents merely for corroboration, background, or "
            "topical similarity. Treat metadata phrases such as `combine with`, `consult`, `use ... before`, or explicit ownership boundaries as routing dependencies when they match a requested output. Select the smallest complete proof set and make its best routing match primary.",
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
            lines.append(f"- {need}")
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
            "Treat facts explicitly supplied by the question as given inputs rather than evidence gaps, and keep "
            "qualifiers attached to the atomic obligation they modify. Resolve obligations independently before "
            "composing the final answer: a rule applicable to one branch must not overwrite a separately requested "
            "base, default, ordinary, excluded, or counterfactual branch. Use disclosed bodies to establish requested "
            "facts and indispensable relationships; do not add background or corroboration requirements after the "
            "fact. Document IDs, titles, and routing-plan mappings are source labels rather than factual answer "
            "values; never substitute one for a requested fact unless the question explicitly asks for that source "
            "identifier. If every planned obligation is established, call submit_answer and put the actual complete "
            "non-empty user-facing answer in its answer field. If one concrete planned obligation is unsupported, "
            "call request_more_evidence with one precise non-empty missing evidence need.",
        ]
    )
    return "\n".join(lines)
