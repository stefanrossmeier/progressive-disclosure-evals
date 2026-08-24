# Progressive Disclosure Evals

An eval-first experiment for measuring whether an LLM can discover the knowledge it actually needs without loading an entire knowledge base.

The current V14 runtime uses a complete-plan metadata-first progressive-disclosure pipeline:

```text
all document id/title/activation-description metadata
                    ↓
        atomic evidence plan (need -> document)
                    ↓
          disclose the distinct planned bodies
                    ↓
       submit_answer / request_more_evidence
             ↙               ↘
          answer       one precise missing fact
                              ↓
                 one bounded recovery selection
```

The normal path is two model calls for both single- and multi-document questions. The runtime is never told how many documents a case requires.

The corpus contains fictional, non-guessable Northstar Systems facts so correct answers can be tied to disclosed evidence rather than model priors.

## Why V14

V9-V11 established that activation-oriented metadata plus explicit selection is highly effective for this corpus. V11's difficult single-document smoke reached 24/24 end-to-end, and the full historical multi-document validation reached 95% discovery / 95% answer accuracy, although strict E2E was reduced by attribution and evaluator-chain issues.

V12 tested a more adaptive design: select 1-2 bodies, regenerate a structured evidence ledger, then route again from the remaining gap. That experiment regressed badly with `gpt-5-nano`: the hard single verification fell to 83.3% E2E and the genuine multi-document development verification to 25% E2E. Raw traces showed that model-authored ledger state was non-monotonic—facts supported in one round became missing in later rounds—and the nested evidence schema caused protocol failures after correct retrieval. V13 therefore returns to a simpler, more reliable mechanism: plan the smallest complete proof set from activation metadata, disclose those bodies once, and use one simple evidence-resolution call. Recovery remains available only for a concrete missing obligation.

V13 then restored complete-plan reliability: the focused `multi-dev-v2` selection diagnostic reached 30/30 top-1 and 30/30 complete initial plans, the hard single-document verification reached 24/24 E2E, and the genuine multi-document verification reached 20/20 discovery/top-1. Its five remaining multi-document failures all occurred after complete discovery because `resolve_evidence` chose answer mode but emitted an empty answer twice. V14 therefore preserves V13 retrieval unchanged and simplifies the evidence-stage interface into two explicit actions: `submit_answer(answer)` or `request_more_evidence(missing_information)`. The stateless retry now also receives the exact protocol defect instead of replaying the same request unchanged.

V13 also fixed two evaluation problems exposed by V12: multi selection diagnostics require complete initial-plan recall rather than merely a gold top-1 document, and `multi-dev-v2` numeric expectations are represented correctly as strings. See:

- `docs/v7-audit-2026-08-23.md`
- `docs/how-to-corpus-metadata.md`
- `docs/v10-single-validation-learning-2026-08-23.md`
- `docs/v11-multi-validation-learning-2026-08-23.md`
- `docs/v12-validation-learning-2026-08-24.md`
- `docs/v13-validation-learning-2026-08-24.md`
- `docs/multi-document-progressive-disclosure.md`

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill OPENAI_API_KEY in .env
python -m pytest
python scripts/validate_corpus.py
python scripts/validate_dataset.py
```

## Diagnostics before end-to-end runs

Measure the answer ceiling with gold evidence supplied directly:

```bash
python scripts/run_diagnostics.py \
  --mode oracle \
  --tag single_doc \
  --runs 1 \
  --dry-run
```

Measure metadata discovery without document bodies or answering:

```bash
python scripts/run_diagnostics.py \
  --mode selection \
  --tag single_doc \
  --runs 1 \
  --dry-run
```

A small diagnostic can target only known hard categories/cases before spending on the whole dataset.

## End-to-end verification and validation

`datasets/eval-v1.yaml` contains 60 cases: 40 evaluator-labeled single-document cases and 20 evaluator-labeled multi-document cases. Those labels are used **only by the benchmark runner to choose cases**. The runtime is not told how many documents the answer requires; it must decide from the question and activation metadata whether one body is sufficient or additional bodies are needed.

**Important:** V9 metadata and architecture were designed after inspecting V7 failures on `eval-v1`, so `eval-v1` is now a validation set, not a final untouched test set. Freeze a new `eval-v2` before making final held-out claims.

Run the small model-backed verification sets first:

```bash
python scripts/run_evals.py --config experiments/verify-single-v1.yaml --dry-run
python scripts/run_evals.py --config experiments/verify-single-v1.yaml

python scripts/run_evals.py --config experiments/verify-multi-v1.yaml --dry-run
python scripts/run_evals.py --config experiments/verify-multi-v1.yaml
```

The single-document verification set has 24 case trials (8 hard cases × 3 repeats); the historical eval-v1 multi verification set has 16 (8 difficult cases × 2 repeats). V14 retains `datasets/multi-dev-v2.yaml` plus `experiments/verify-multi-v2.yaml`, a 20-trial genuine multi-document development set where every required body contributes a distinct requested fact or transformation.

Then run the larger validations independently:

```bash
# 40 cases × 5 repeats = 200 single-document case trials
python scripts/run_evals.py --config experiments/eval-single-v1.yaml --dry-run
python scripts/run_evals.py --config experiments/eval-single-v1.yaml

# 20 cases × 5 repeats = 100 multi-document case trials
python scripts/run_evals.py --config experiments/eval-multi-v1.yaml --dry-run
python scripts/run_evals.py --config experiments/eval-multi-v1.yaml
```

CLI `--case` and `--tag` filters only narrow the subset configured by an experiment file; they cannot broaden a single-document config into multi-document cases or vice versa.

Generated runs write `trials.jsonl`, `manifest.json`, `summary.json`, and `report.md` under `results/` and are ignored by Git.

See `docs/methodology.md` and `docs/eval-design.md` for the mechanism and metrics.

## Multi-document development

```bash
python scripts/validate_dataset.py --dataset datasets/multi-dev-v2.yaml
python scripts/run_evals.py --config experiments/verify-multi-v2.yaml --dry-run
python scripts/run_evals.py --config experiments/verify-multi-v2.yaml
```

This development set is intentionally not held out; use it to improve genuine multi-document planning and composition, then freeze a new untouched multi-document benchmark for final claims.
