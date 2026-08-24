from __future__ import annotations

import argparse
import json

from evals.agent_dev import evaluate_case, load_dev_cases, result_to_dict
from progressive_disclosure.config import (
    get_openai_model,
    get_openai_reasoning_effort,
    get_openai_text_verbosity,
    load_project_env,
)
from progressive_disclosure.llm import OpenAIResponsesBackend
from progressive_disclosure.prompts import DEFAULT_AGENT_PROMPT_PATH, load_prompt_artifact


def main() -> int:
    load_project_env()
    parser = argparse.ArgumentParser(description="Run metadata-first progressive-disclosure dev cases.")
    parser.add_argument("--model", default=get_openai_model())
    parser.add_argument("--case", help="Run only one case ID")
    parser.add_argument(
        "--prompt",
        default=str(DEFAULT_AGENT_PROMPT_PATH),
        help="Versioned agent system-prompt artifact",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=4,
        help="Maximum full document bodies the agent may load.",
    )
    args = parser.parse_args()
    if not args.model:
        parser.error("provide --model or set OPENAI_MODEL in .env")

    cases = load_dev_cases()
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            parser.error(f"unknown case: {args.case}")

    prompt = load_prompt_artifact(args.prompt)
    backend = OpenAIResponsesBackend(
        args.model,
        reasoning_effort=get_openai_reasoning_effort(),
        text_verbosity=get_openai_text_verbosity(),
    )
    overall_ok = True
    for case in cases:
        result = evaluate_case(
            case,
            backend=backend,
            max_documents=args.max_documents,
            prompt=prompt,
        )
        payload = result_to_dict(result)
        payload["model_config"] = {
            "model": args.model,
            "reasoning_effort": backend.reasoning_effort,
            "text_verbosity": backend.text_verbosity,
        }
        print(json.dumps(payload, indent=2))
        overall_ok &= result.overall_success
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
