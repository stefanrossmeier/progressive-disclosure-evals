import os
from pathlib import Path

from evals.benchmark import (
    BenchmarkPlan,
    load_eval_dataset,
    load_plan,
    resolve_case_filters,
    select_cases,
)


def test_eval_dataset_loader_exposes_named_versioned_dataset():
    data = load_eval_dataset("datasets/eval-v1.yaml")
    assert data["name"] == "eval-v1"
    assert data["version"] == 1
    assert len(data["cases"]) == 60


def test_case_selection_supports_case_ids_and_tags():
    cases = load_eval_dataset("datasets/eval-v1.yaml")["cases"]
    selected = select_cases(cases, tags={"multi_doc", "precedence"})
    assert selected
    assert all("multi_doc" in case["tags"] and "precedence" in case["tags"] for case in selected)
    selected = select_cases(cases, case_ids={"EVAL-001"})
    assert [case["id"] for case in selected] == ["EVAL-001"]


def test_plan_resolves_model_from_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    plan = load_plan("experiments/eval-v1.yaml")
    assert plan.models == ("test-model",)
    assert plan.runs_per_case == 5
    assert plan.max_documents == 4
    assert plan.prompts == (Path("prompts/agent/system-v14.md"),)


def test_prompt_comparison_plan_has_two_compatible_prompts(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    plan = load_plan("experiments/prompt-comparison.yaml")
    assert len(plan.prompts) == 2
    assert Path("prompts/agent/system-v7.md") in plan.prompts
    assert Path("prompts/agent/system-v8.md") in plan.prompts


def test_default_output_dir_is_collision_resistant():
    from evals.benchmark import default_output_dir

    first = default_output_dir("eval")
    second = default_output_dir("eval")
    assert first != second
    assert first.parent == Path("results")
    assert second.parent == Path("results")


def test_artifact_hashes_are_stable_and_content_sensitive(tmp_path):
    from evals.benchmark import _corpus_sha256, _sha256_file

    file_path = tmp_path / "dataset.yaml"
    file_path.write_text("a: 1\n", encoding="utf-8")
    first = _sha256_file(file_path)
    assert first == _sha256_file(file_path)
    file_path.write_text("a: 2\n", encoding="utf-8")
    assert first != _sha256_file(file_path)

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text("alpha\n", encoding="utf-8")
    corpus_hash = _corpus_sha256(corpus)
    (corpus / "a.md").write_text("beta\n", encoding="utf-8")
    assert corpus_hash != _corpus_sha256(corpus)


def test_benchmark_refuses_to_append_to_existing_trials(tmp_path, monkeypatch):
    from evals.benchmark import BenchmarkPlan, run_benchmark

    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    output = tmp_path / "existing"
    output.mkdir()
    (output / "trials.jsonl").write_text("already here\n", encoding="utf-8")
    plan = BenchmarkPlan(
        name="test",
        dataset=Path("datasets/eval-v1.yaml"),
        runs_per_case=1,
        max_documents=1,
        prompts=(Path("prompts/agent/system-v7.md"),),
        models=("test-model",),
    )

    import pytest

    with pytest.raises(FileExistsError, match="refusing to append"):
        run_benchmark(plan, output_dir=output, limit=1, quiet=True)


def test_separate_single_and_multi_plans_select_disjoint_eval_slices(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    dataset = load_eval_dataset("datasets/eval-v1.yaml")
    single = load_plan("experiments/eval-single-v1.yaml")
    multi = load_plan("experiments/eval-multi-v1.yaml")

    single_ids, single_tags = resolve_case_filters(single)
    multi_ids, multi_tags = resolve_case_filters(multi)
    single_cases = select_cases(dataset["cases"], case_ids=single_ids, tags=single_tags)
    multi_cases = select_cases(dataset["cases"], case_ids=multi_ids, tags=multi_tags)

    assert len(single_cases) == 40
    assert len(multi_cases) == 20
    assert {case["id"] for case in single_cases}.isdisjoint(
        {case["id"] for case in multi_cases}
    )
    assert all("single_doc" in case["tags"] for case in single_cases)
    assert all("multi_doc" in case["tags"] for case in multi_cases)


def test_verification_plans_are_small_fixed_subsets(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    dataset = load_eval_dataset("datasets/eval-v1.yaml")

    single = load_plan("experiments/verify-single-v1.yaml")
    single_ids, single_tags = resolve_case_filters(single)
    single_cases = select_cases(dataset["cases"], case_ids=single_ids, tags=single_tags)
    assert [case["id"] for case in single_cases] == [
        "EVAL-001", "EVAL-004", "EVAL-012", "EVAL-015",
        "EVAL-020", "EVAL-024", "EVAL-026", "EVAL-033",
    ]
    assert all("single_doc" in case["tags"] for case in single_cases)

    multi = load_plan("experiments/verify-multi-v1.yaml")
    multi_ids, multi_tags = resolve_case_filters(multi)
    multi_cases = select_cases(dataset["cases"], case_ids=multi_ids, tags=multi_tags)
    assert [case["id"] for case in multi_cases] == [
        "EVAL-041", "EVAL-043", "EVAL-047", "EVAL-048",
        "EVAL-052", "EVAL-053", "EVAL-057", "EVAL-058",
    ]
    assert all("multi_doc" in case["tags"] for case in multi_cases)


def test_cli_case_filter_can_only_narrow_configured_subset():
    plan = BenchmarkPlan(
        name="single",
        dataset=Path("datasets/eval-v1.yaml"),
        runs_per_case=1,
        max_documents=4,
        prompts=(Path("prompts/agent/system-v14.md"),),
        models=("test-model",),
        case_tags=("single_doc",),
    )
    case_ids, tags = resolve_case_filters(plan, case_ids={"EVAL-001"}, tags={"commercial"})
    assert case_ids == {"EVAL-001"}
    assert tags == {"single_doc", "commercial"}


def test_v18_allows_two_bounded_recoveries_while_v17_keeps_historical_default(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    v18 = load_plan("experiments/v18/tell-aster/eval-single-v1.yaml")
    v17 = load_plan("experiments/v17/tell-aster/eval-single-v1.yaml")
    assert v18.max_selection_rounds == 3
    assert v17.max_selection_rounds == 2
    assert v18.dataset == Path("datasets/tell-aster-eval-v2.yaml")
    assert v17.dataset == Path("datasets/tell-aster-eval-v1.yaml")
