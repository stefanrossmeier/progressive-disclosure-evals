# Methodology

## Mechanism under test

V14 intentionally follows a metadata-first progressive-disclosure pattern rather than custom tree search or a retrieval framework.

1. **Activation metadata** — The model receives `id`, `title`, and a retrieval-oriented `description` for every available document. Paths and bodies are not included.
2. **Complete atomic evidence planning** — A forced `select_documents` call decomposes the requested outputs and maps each required fact/transformation/precedence premise to a document ID. The first document is the explicit top-1 routing decision. Multiple obligations may map to the same body.
3. **Body disclosure** — The runtime discloses only the distinct bodies in that plan, up to the global document budget.
4. **Evidence action** — The model must choose exactly one of two small tools: `submit_answer(answer)` when the disclosed bodies establish the plan, or `request_more_evidence(missing_information)` for one precise unsupported obligation. Final citations are derived from the model-authored evidence plan rather than asking the model to reproduce the source list again.
5. **Bounded recovery** — One additional metadata-selection round is available for that concrete gap. There is no model-authored evidence ledger carried across arbitrary rounds.

The runtime is deliberately **task-type agnostic**. It is never told whether an eval case is labeled `single_doc` or `multi_doc`, how many gold documents exist, which documents are required, or what answer values the evaluator expects. The selector infers the proof set from the natural-language question and activation metadata.

There is no directory-navigation protocol, vector database, embedding search, reranker, planner agent, or hidden gold-path assistance.

This design remains close to established progressive-disclosure guidance: compact discovery metadata points to deeper source material, while full bodies are loaded only for selected authorities.

References:

- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://openai.com/index/harness-engineering/

## Why complete planning is explicit

V12 showed that repeated model-authored evidence ledgers are not reliable enough with `gpt-5-nano`: supported findings disappeared between rounds, exclusions became new evidence requirements, and the nested structured response increased protocol failures. See `docs/v12-validation-learning-2026-08-24.md`. V13 then proved that complete planning could reach 100% discovery on the focused genuine multi-document gate; its remaining failures were empty-answer protocol actions after complete discovery. See `docs/v13-validation-learning-2026-08-24.md`.

V14 preserves V13 complete planning and therefore uses the activation catalog for what it is good at: deciding which bodies contain the distinct requested facts. The evidence bodies are then used for synthesis and verification.

For both a successful single-document task and a predictable multi-document task, the ideal path is two model calls:

```text
metadata -> complete evidence plan
selected bodies -> answer
```

A recovery path can take four calls when one planned obligation is genuinely unsupported.

Important planning rules:

- facts explicitly stated by the question are inputs, not evidence gaps;
- a negative qualifier excludes a routing branch but does not require documentary proof of absence;
- default/normal/base values must remain distinct from regional/effective/lower/actual values when both are requested;
- multi-document selection diagnostics require complete initial proof-set recall, not merely a correct top-1 document.

## Metadata policy

Metadata is allowed to contain routing vocabulary supplied by the user, including named markers such as `MIG-2`, `D-8`, `PINE-6`, `P-17`, or `EX-TEMP`, when those identifiers distinguish which authority should be opened.

Metadata must not contain the hidden team/code/threshold/duration/queue facts that form the answer.

See `docs/how-to-corpus-metadata.md`.

## What the eval measures

For each case the evaluator knows required documents and expected answer values, but the runtime never receives that gold data.

Primary dimensions:

- top-1 primary-document accuracy;
- required-document recall and precision;
- final-answer correctness;
- source attribution;
- unnecessary selected/read documents;
- recovery behavior;
- model calls and API tokens;
- metadata size versus disclosed document content.

Selection-only and oracle-answer diagnostics isolate the two main ceilings before an end-to-end run.
