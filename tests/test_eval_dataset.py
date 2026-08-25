from pathlib import Path

import yaml

from progressive_disclosure.corpora import get_corpus_spec
from progressive_disclosure.knowledge import KnowledgeBase
from scripts.validate_dataset import validate_dataset


def load_cases(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))["cases"]


def test_registered_benchmark_datasets_are_valid_and_exhaustive():
    expected = {"northstar": (60, 40, 20), "tell-aster": (120, 80, 40)}
    for name, (total, single, multi) in expected.items():
        spec = get_corpus_spec(name)
        assert validate_dataset(spec.default_dataset, corpus_name=name) == []
        cases = load_cases(spec.default_dataset)
        knowledge = KnowledgeBase(spec.root)
        covered = {doc for case in cases for doc in case["required_documents"]}
        assert len(cases) == total
        assert sum(len(case["required_documents"]) == 1 for case in cases) == single
        assert sum(len(case["required_documents"]) > 1 for case in cases) == multi
        assert covered == set(knowledge.document_ids)


def test_expected_values_are_not_in_questions_and_exist_in_required_evidence():
    for name in ("northstar", "tell-aster"):
        spec = get_corpus_spec(name)
        knowledge = KnowledgeBase(spec.root)
        for case in load_cases(spec.default_dataset):
            q = case["question"].casefold()
            evidence = "\n".join(knowledge.read(doc).content for doc in case["required_documents"]).casefold()
            for value in case["expected_contains"]:
                assert value.casefold() not in q, case["id"]
                assert value.casefold() in evidence, (case["id"], value)


def test_case_ids_are_unique_within_each_benchmark():
    for name in ("northstar", "tell-aster"):
        spec = get_corpus_spec(name)
        ids = [case["id"] for case in load_cases(spec.default_dataset)]
        assert len(ids) == len(set(ids))


def test_tell_aster_multi_cases_separate_answer_expectations_from_required_evidence():
    spec = get_corpus_spec("tell-aster")
    cases = load_cases(spec.default_dataset)
    multi = [case for case in cases if len(case["required_documents"]) > 1]
    assert len(multi) == 40
    for case in multi:
        assert set(case["required_evidence"]) == set(case["required_documents"])
        assert all(case["required_evidence"][doc] for doc in case["required_documents"])

    by_id = {case["id"]: case for case in multi}
    assert by_id["TA-M-001"]["expected_contains"] == ["Aster-RC-117", "1010–930 BCE"]
    assert "Aster-RC-117 was taken from the charcoal-rich Room 6 destruction layer" in by_id["TA-M-001"]["required_evidence"]["TA-EXC-02"]
    assert by_id["TA-M-037"]["expected_contains"] == ["Anomaly M-17", "Transect P4"]


def test_tell_aster_count_cases_keep_contextual_gold_phrases_for_leakage_checks():
    cases = {case["id"]: case for case in load_cases(get_corpus_spec("tell-aster").default_dataset)}
    expected = {
        "TA-S-009": ["five resurfacing episodes"],
        "TA-S-012": ["Six doorways"],
        "TA-S-017": ["three"],
        "TA-S-029": ["17 socketed arrowheads"],
        "TA-S-043": ["four ceramic vessels"],
        "TA-S-079": ["31 graves"],
        "TA-M-008": ["Aster-RC-204", "five resurfacing episodes"],
        "TA-M-020": ["Burial B-14", "four ceramic vessels"],
        "TA-M-023": ["Melanopsis", "Six doorways"],
        "TA-M-030": ["B-17", "31 graves"],
    }
    for case_id, values in expected.items():
        assert cases[case_id]["expected_contains"] == values


def test_tell_aster_reinterpretation_answer_grades_semantic_value_not_required_wording():
    cases = {case["id"]: case for case in load_cases(get_corpus_spec("tell-aster").default_dataset)}
    case = cases["TA-M-005"]
    assert case["expected_contains"][0] == "workshop hearth"
    assert case["required_evidence"]["TA-EXC-06"] == ["initially interpreted as a workshop hearth"]


def test_tell_aster_reinterpretation_case_explicitly_requests_every_graded_fact():
    cases = {case["id"]: case for case in load_cases(get_corpus_spec("tell-aster").default_dataset)}
    case = cases["TA-M-005"]
    assert "initially interpreted" in case["question"].casefold()
    assert "botanical" in case["question"].casefold()
    assert "architectural" in case["question"].casefold()
    assert set(case["required_evidence"]) == set(case["required_documents"])


def test_tell_aster_release_corpus_is_physically_separate_from_eval_gold():
    spec = get_corpus_spec("tell-aster")
    assert spec.root == Path("corpus/tell-aster")
    assert spec.default_dataset == Path("datasets/tell-aster-eval-v2.yaml")
    assert spec.default_dataset.is_file()
    assert not list(spec.root.rglob("*.yaml"))
    assert not list(spec.root.rglob("*.yml"))
    assert not any("eval" in path.name.casefold() for path in spec.root.rglob("*"))


def test_tell_aster_release_multi_questions_request_at_least_one_output_per_gold_document():
    cases = load_cases(get_corpus_spec("tell-aster").default_dataset)
    multi = [case for case in cases if len(case["required_documents"]) > 1]
    assert len(multi) == 40
    for case in multi:
        assert len(case["expected_contains"]) >= len(case["required_documents"]), case["id"]


def test_tell_aster_historical_v1_remains_external_and_valid():
    historical = Path("datasets/tell-aster-eval-v1.yaml")
    assert historical.is_file()
    assert validate_dataset(historical, corpus_name="tell-aster") == []
    data = yaml.safe_load(historical.read_text(encoding="utf-8"))
    assert data["version"] == 1
