# Evaluation

This repository evaluates progressive disclosure over a 40-document Markdown corpus with `gpt-5-nano`. The agent selects relevant documents from metadata and answers using only the disclosed document bodies.

> The results below are development/verification results, not an untouched held-out benchmark.

## Run the evals

First validate the repository and datasets:

```bash
python -m pytest
python scripts/validate_corpus.py
python scripts/validate_dataset.py
python scripts/validate_dataset.py --dataset datasets/multi-dev-v2.yaml
```

Run the single-document hard gate:

```bash
python scripts/run_evals.py --config experiments/verify-single-v1.yaml
```

Run the genuine multi-document composition gate:

```bash
python scripts/run_evals.py --config experiments/verify-multi-v2.yaml
```

Each run writes `trials.jsonl`, `summary.json`, and `report.md` under `results/`.

## Recent results

| Evaluation | Version | Trials | E2E success | Discovery | First-read hit | Attribution | Mean docs | Mean model calls |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single-document hard gate | V13 | 24 | **100%** | **100%** | **100%** | **100%** | 1.54 | 2.08 |
| Multi-document composition | V14 | 20 | **95%** | **100%** | **100%** | **100%** | 3.20 | 2.00 |

The V14 multi-document run succeeded on 19/20 trials. All 20 trials discovered the complete required evidence set and attributed the answer correctly; the single failure was an answer-composition error, not a retrieval failure.

The latest single-document hard-gate result is still the V13 run shown above. V14 changed the final answer-action interface, so single-document performance should be rerun before claiming a same-version V14 result.
