# Tell Aster Expedition Evaluation Corpus

This package contains a fully fictional archaeological archive for evaluating progressive-disclosure document retrieval. It is intentionally unrelated to enterprise software, SaaS operations, policy routing, governance, billing, incident response, or similar domains.

## Contents

- `corpus/tell-aster/` — 80 Markdown research records with activation metadata (`id`, `title`, `description`) in YAML front matter.
- `datasets/tell-aster-eval-v1.yaml` — historical evaluator-only benchmark.
- `datasets/tell-aster-eval-v2.yaml` — current release benchmark with 80 single-document cases and 40 multi-document cases.
- `scripts/validate_corpus.py` / `scripts/validate_dataset.py` — repository-wide structural, evidence, coverage, cross-reference, and metadata-leak validators.
- `docs/tell-aster-audit.md` — benchmark-quality and metadata-leak audit.

The dataset file contains evaluator-only fields such as `required_documents`, tags, and expected strings. Do not expose those fields to the runtime retrieval agent. Runtime progressive disclosure should expose only the corpus activation metadata until a document body is selected.

## Archive character

The archive represents a long-running excavation at the fictional settlement of Tell Aster. It includes excavation journals and stratigraphy, architecture, pottery, small finds, inscriptions, burials and osteology, environmental studies, dating reports, conservation and museum records, remote sensing and geology, and synthetic/correspondence material.

The corpus deliberately contains recurring identifiers, revised interpretations, nearby samples, similar artifact numbers, parallel burial records, and cross-specialist references. Important eval facts are embedded within larger research records rather than concentrated in activation descriptions.

## Statistics

- Corpus documents: **80**
- Approximate corpus body words: **76,311**
- Corpus characters (including front matter): **585,462**
- Documents at or above ~1,000 body words: **61/80**
- Short technical records: primarily dating, conservation, and survey reports (**690–715 words minimum range across those series**)
- Explicit document-ID cross-reference mentions: **478**
- Unique directed document-to-document links: **398**
- Single-document eval cases: **80**
- Multi-document eval cases: **40**
- Total eval cases: **120**
- Corpus coverage by evals: **80/80 documents (100%)**

Category counts:

| Category | Documents |
|---|---:|
| excavation / stratigraphy | 10 |
| architecture / spatial analysis | 8 |
| pottery / ceramics | 8 |
| artifacts / small finds | 7 |
| inscriptions / written material | 7 |
| burial / osteology | 7 |
| botanical / faunal / environmental | 7 |
| dating / laboratory analysis | 7 |
| conservation / museum / provenance | 6 |
| survey / geology / remote sensing | 6 |
| synthesis / correspondence / season review | 7 |

## Validation

From the repository root:

```bash
python scripts/validate_corpus.py --corpus tell-aster
python scripts/validate_dataset.py --dataset datasets/tell-aster-eval-v2.yaml --corpus tell-aster
python -m pytest
```

No paid model evaluations are included or invoked.

The corpus and benchmark now use the repository's generic multi-corpus schema. Evaluator gold is physically outside `corpus/tell-aster/` and is never part of the runtime catalog.
