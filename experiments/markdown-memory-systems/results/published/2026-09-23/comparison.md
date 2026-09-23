# Markdown-memory retrieval comparison — final valid full runs

The final comparable full runs include **ai-memory 2.4.0** and **agent-memory `70d85e5c22081d9dac88c5e908c88ea0bf13af88`**. EverOS 1.3.1 is intentionally excluded from this table because its keyword path did not return Tell Aster hits reliably in the final smoke probe; no full EverOS score is claimed.

| Backend | Answer | Discovery | Answer + discovery | Single-doc A+D | Multi-doc A+D | Attribution | Mean docs | Mean retrieval |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **agent-memory** | 98.3% | **97.8%** | **96.7%** | **100.0%** | **90.0%** | **95.0%** | 6.00 | 75.0 ms |
| **ai-memory** | **98.9%** | 97.2% | 96.1% | **100.0%** | 88.3% | 93.9% | 6.00 | **16.4 ms** |

## By corpus

| Backend | Northstar A+D | Northstar single | Northstar multi | Tell Aster A+D | Tell Aster single | Tell Aster multi |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **agent-memory** | **93.3%** | **100.0%** | **80.0%** | 98.3% | **100.0%** | 95.0% |
| **ai-memory** | 91.7% | **100.0%** | 75.0% | 98.3% | **100.0%** | 95.0% |

## Failure overlap

Using Answer + discovery, ai-memory fails 7 cases and agent-memory fails 6. Four failures overlap:

```text
EVAL-044
EVAL-045
TA-M-015
TA-M-025
```

Their diagnostic union therefore passes 176/180 cases. This is not an implemented ensemble score and the two corpora are development/validation corpora.
