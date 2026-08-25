import json
from pathlib import Path

from evals.aggregate import aggregate, load_records, render_markdown, write_aggregate


def record(
    case,
    repeat,
    *,
    success,
    reads,
    wrong,
    after,
    model="nano",
    prompt=7,
    tag="single_doc",
    dataset_sha="dataset-a",
    corpus_sha="corpus-a",
    prompt_sha="prompt-a",
    corpus_name="northstar",
):
    return {
        "status": "completed",
        "case_id": case,
        "repeat_index": repeat,
        "model": model,
        "prompt_id": "progressive-disclosure-agent-system",
        "prompt_version": prompt,
        "prompt_sha256": prompt_sha,
        "dataset_sha256": dataset_sha,
        "corpus_sha256": corpus_sha,
        "corpus_name": corpus_name,
        "tags": [tag],
        "required_documents": ["doc.a"],
        "result": {
            "overall_success": success,
            "answer_contains_expected": success,
            "required_sources_cited": success,
            "document_reads": reads,
            "model_turns": reads + 1,
            "input_tokens": 1000 * reads,
            "output_tokens": 100,
            "discovery": {
                "complete_discovery": success,
                "document_precision": 1 / reads if success else 0.0,
                "wrong_documents_before_first_gold": wrong,
                "reads_after_complete_discovery": after if success else None,
            },
            "context": {"knowledge_content_fraction_loaded": reads / 40},
        },
    }


def error_record(case="EVAL-ERR", *, error_type="RateLimitError"):
    return {
        "status": "error",
        "case_id": case,
        "repeat_index": 1,
        "model": "nano",
        "prompt_id": "progressive-disclosure-agent-system",
        "prompt_version": 7,
        "prompt_sha256": "prompt-a",
        "dataset_sha256": "dataset-a",
        "corpus_sha256": "corpus-a",
        "tags": ["single_doc"],
        "required_documents": ["doc.a"],
        "error_type": error_type,
        "error_message": "synthetic error",
    }


def test_aggregate_reports_success_discovery_stopping_and_variability():
    records = [
        record("EVAL-001", 1, success=True, reads=1, wrong=0, after=0),
        record("EVAL-001", 2, success=True, reads=4, wrong=0, after=3),
        record("EVAL-002", 1, success=False, reads=4, wrong=4, after=None),
    ]
    summary = aggregate(records)
    assert summary["schema_version"] == 2
    assert summary["overall"]["completed"] == 3
    assert summary["overall"]["overall_success_rate"] == 2 / 3
    assert summary["overall"]["end_to_end_success_rate"] == 2 / 3
    assert summary["overall"]["evidence_stopping_rate"] == 0.5
    assert summary["by_case"]["EVAL-001"]["overall_success_rate"] == 1.0
    assert "1" in summary["by_repeat"]
    assert summary["overall"]["std_document_reads"] > 0




def test_aggregate_groups_cross_corpus_suites_by_corpus():
    records = [
        record("EVAL-001", 1, success=True, reads=1, wrong=0, after=0, corpus_name="northstar"),
        record("TA-S-001", 1, success=True, reads=1, wrong=0, after=0, corpus_name="tell-aster"),
    ]
    summary = aggregate(records)
    assert set(summary["by_corpus"]) == {"northstar", "tell-aster"}
    text = render_markdown(summary)
    assert "By corpus" in text

def test_aggregate_exposes_errors_and_end_to_end_success_separately():
    records = [
        record("EVAL-001", 1, success=True, reads=1, wrong=0, after=0),
        error_record(),
    ]
    summary = aggregate(records)
    overall = summary["overall"]
    assert overall["trials"] == 2
    assert overall["completed"] == 1
    assert overall["errors"] == 1
    assert overall["completion_rate"] == 0.5
    assert overall["overall_success_rate"] == 1.0
    assert overall["end_to_end_success_rate"] == 0.5
    assert summary["errors_by_type"] == {"RateLimitError": 1}


def test_report_has_valid_prompt_model_label_and_full_quality_metrics():
    summary = aggregate(
        [
            record(
                "EVAL-001",
                1,
                success=True,
                reads=1,
                wrong=0,
                after=0,
                model="model|variant",
            )
        ]
    )
    text = render_markdown(summary)
    assert "Prompt × model comparison" in text
    assert "By prompt" in text
    assert "By model" in text
    assert "Answer" in text
    assert "Attribution" in text
    assert "E2E success" in text
    # Markdown cell separators inside arbitrary labels must be escaped.
    assert "model\\|variant :: progressive-disclosure-agent-system@v7#prompt-a" in text


def test_report_marks_stopping_variability_even_when_all_answers_pass():
    summary = aggregate(
        [
            record("EVAL-001", 1, success=True, reads=1, wrong=0, after=0),
            record("EVAL-001", 2, success=True, reads=4, wrong=0, after=3),
        ]
    )
    text = render_markdown(summary)
    variable_section = text.split("## Run-to-run variable cases", 1)[1]
    assert "EVAL-001" in variable_section


def test_hardest_cases_consider_stopping_and_overreading_not_only_pass_fail():
    summary = aggregate(
        [
            record("EVAL-EFFICIENT", 1, success=True, reads=1, wrong=0, after=0),
            record("EVAL-OVERREAD", 1, success=True, reads=4, wrong=0, after=3),
        ]
    )
    text = render_markdown(summary)
    hardest = text.split("## Hardest cases", 1)[1].split("## Run-to-run variable cases", 1)[0]
    assert hardest.index("EVAL-OVERREAD") < hardest.index("EVAL-EFFICIENT")


def test_provenance_warns_when_corpus_versions_are_mixed():
    records = [
        record("EVAL-001", 1, success=True, reads=1, wrong=0, after=0, corpus_sha="corpus-a"),
        record("EVAL-002", 1, success=True, reads=1, wrong=0, after=0, corpus_sha="corpus-b"),
    ]
    text = render_markdown(aggregate(records))
    assert "multiple corpus content fingerprints" in text


def test_old_records_without_hashes_remain_aggregatable():
    old = record("EVAL-001", 1, success=True, reads=1, wrong=0, after=0)
    old.pop("dataset_sha256")
    old.pop("corpus_sha256")
    old.pop("prompt_sha256")
    summary = aggregate([old])
    assert summary["overall"]["completed"] == 1
    assert summary["provenance"]["records_without_prompt_hash"] == 1
    assert "provenance is incomplete" in render_markdown(summary)


def test_jsonl_loading_and_report_writing(tmp_path):
    path = tmp_path / "trials.jsonl"
    path.write_text(
        json.dumps(record("EVAL-001", 1, success=True, reads=1, wrong=0, after=0)) + "\n",
        encoding="utf-8",
    )
    records = load_records([path])
    assert len(records) == 1
    summary_path, report_path = write_aggregate(records, tmp_path)
    assert summary_path.is_file()
    assert report_path.is_file()
