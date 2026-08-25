# How to design the progressive-disclosure runtime protocol

## Purpose

The runtime should preserve the simplest reliable flow:

```text
question + compact metadata
    -> complete atomic evidence plan
    -> disclose planned bodies
    -> answer, or request one precise missing fact
```

The protocol should not manufacture an additional global interpretation of the question when the evidence plan can carry the required scope directly.

## Keep scope local to atomic evidence obligations

Compound questions often contain conditions that apply to only one requested fact. Store those conditions in the `need` that represents that fact.

Good:

```text
need: EU policy cap for an ordinary Atlas outage credit
need: team/code governing the MIG-2 migration credit instead
```

Bad:

```text
active qualifiers: EU, Atlas, MIG-2, outage
```

A global qualifier list loses which modifier belongs to which clause. In V16 this produced repeated failures where `MIG-2` modified an independent ordinary-outage obligation and where an EU condition overrode a counterfactual request that explicitly asked for the default behavior without the regional replacement.

The evidence plan is already the structured state. Do not add a second global scope representation unless measurements prove it is necessary.

## Treat negation and counterfactuals as operators, not keywords

Negative or counterfactual wording must stay attached to the obligation it modifies.

- `non-X` means X is excluded for that obligation. Never convert lexical overlap with `X` into an active X condition.
- `without X` means answer that obligation under X absent, even if X is relevant elsewhere in the same question.
- `instead`, `whereas`, `rather than`, and similar contrast words create branch boundaries. Do not transfer modifiers across those branches.

This is stronger than remembering positive and negative words separately. The model must preserve the scoped proposition.

## Make every evidence-plan need self-contained

A good `need` can be read without the neighboring obligations and still retain the relevant entity, scope, negation, and counterfactual condition.

Prefer wording copied closely from the originating clause of the question. Free paraphrase is risky when two clauses share related vocabulary.

For example:

```text
question:
For an EU-governed Atlas-to-Zephyr migration marked MIG-2,
what cap would the EU policy use for an ordinary Atlas outage credit,
and which team/code govern the MIG-2 migration credit instead?
```

The first obligation must remain an **ordinary Atlas outage credit** obligation. The phrase `MIG-2 migration credit` belongs to the second obligation only.

## Do not expose redundant model-generated routing state

Every structured field is another opportunity for the model to create an internally inconsistent interpretation.

A field is justified only if downstream code needs it for execution or if measurement shows that it improves reliability enough to offset the extra state.

V16 exposed `active_qualifiers` and `excluded_qualifiers` even though selection and attribution were driven by `evidence_plan`. Raw traces showed contradictory states such as `non-EU` together with active `EU`. V17 removes those arrays from the model-facing schema and from runtime traces.

Diagnostics should inspect the evidence-plan obligations themselves rather than a lossy parallel summary.

## Keep routing labels out of factual answering

Document IDs, titles, metadata descriptions, and evidence-plan mappings are routing/source labels. They are not factual answer values unless the user explicitly asks for such an identifier.

The answer stage should receive:

- the original question;
- the textual evidence obligations;
- disclosed document bodies.

It does not need `need -> document_id` mappings in the prose supplied to the answer model. Attribution can be derived mechanically from the internal evidence plan.

## Recovery is for one real evidence gap

After disclosure, request more evidence only when one concrete planned obligation cannot be established from the opened bodies.

Do not use recovery to:

- reconfirm a fact explicitly supplied in the question;
- prove an excluded branch absent;
- collect background or corroboration;
- repair a scope mistake that was introduced by the evidence plan itself.

If scope is wrong, fix the selection representation or prompt. Additional retrieval usually compounds the error.

## Diagnose failures by stage

For every failed trial, inspect the raw trace and classify separately:

1. Did the first evidence plan contain every genuinely necessary document?
2. Did each `need` preserve the clause-local scope from the question?
3. Were unnecessary documents selected because of metadata ambiguity?
4. Once sufficient evidence was disclosed, did the answer use the correct body values?
5. Did the run stop after sufficient evidence?
6. Is the evaluator requiring wording rather than the semantic value requested by the question?
7. Is every gold document genuinely indispensable?

Do not alter retrieval when the correct bodies were already open, and do not tune prompts around an evaluator false negative.

## Versioning discipline

Keep every measured runtime prompt immutable. A new prompt or protocol change gets a new version and new experiment configs.

A verification gate is for detecting regressions and validating a specific fix. Do not make a strong generalization claim from a small verification slice, and do not run the expensive full benchmark while a systematic verification failure remains unexplained.

## Release guidance: progressive discovery, not blind retry

The release runtime follows the same broad context-engineering pattern described by Anthropic and OpenAI:

- start from a compact, stable map rather than loading the whole knowledge base;
- make metadata descriptive enough to support routing decisions;
- disclose full bodies only after selection;
- let information discovered in one layer guide navigation to the next layer;
- keep the recovery protocol bounded and mechanically inspectable.

Official references:

- Anthropic, *Equipping agents for the real world with Agent Skills*: metadata is the first level of progressive disclosure, the selected skill body the second, and linked files deeper levels. https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Anthropic, *Effective context engineering for AI agents*: context is finite; progressive disclosure allows an agent to discover relevant context incrementally, while exploration must be guided to avoid dead ends. https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- OpenAI, *Harness engineering*: give an agent a map rather than a giant instruction manual; catalogue and index knowledge and enforce the structure mechanically. https://openai.com/index/harness-engineering/
- OpenAI, *A practical guide to building agents*: standardized, well-documented tools improve discoverability and reduce redundant definitions. https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf

### Carry compact navigation clues forward

A recovery selection should not forget the useful navigation information exposed by the previous document read. Full opened bodies do not need to be copied back into the selector, but explicit cross-references discovered in them are cheap routing hints.

Use this pattern:

```text
metadata map
  -> selected body
  -> unresolved fact
  -> referenced-document IDs + remaining metadata
  -> targeted recovery
```

Reference IDs are **hints, not evidence and not mandatory edges**. Follow one only when its activation metadata matches the unresolved obligation. This preserves progressive discovery without turning the knowledge base into an implicit graph traversal algorithm.

### Keep recovery bounded but allow a second targeted attempt

One recovery attempt was too brittle for larger, cross-domain metadata catalogs: several V17 failures chose one plausible document, then one second plausible document, and terminated immediately before reaching the correct owner. V18 permits up to three selection rounds while keeping the document budget at four. This is still a bounded stateless protocol; it does not reintroduce the fragile multi-round evidence ledger used by earlier experiments.

The important limits are therefore separate:

- **document budget** limits how much knowledge is disclosed;
- **selection-round budget** limits navigation attempts;
- recovery occurs only after the answer stage names one concrete missing obligation.

### Treat explicit metadata dependencies as routing instructions

Descriptions such as "combine with geomorphology when the question asks for the named terrace" or "use the field report for the original interpretation; use the synthesis for the later reassessment" are not decorative prose. They define ownership boundaries and predictable dependencies.

When such a boundary exactly matches a requested output, plan it up front. Do not wait for a failed answer call to rediscover a dependency that the metadata already stated.
