from pathlib import Path

import yaml

from progressive_disclosure.knowledge import KnowledgeBase
from scripts.validate_dataset import validate_dataset


def load_cases():
    return yaml.safe_load(Path("datasets/eval-v1.yaml").read_text(encoding="utf-8"))["cases"]


def test_eval_v1_is_valid_and_exhaustive_over_corpus():
    assert validate_dataset(Path("datasets/eval-v1.yaml"), Path("corpus/northstar")) == []
    cases = load_cases()
    knowledge = KnowledgeBase("corpus/northstar")
    covered = {doc for case in cases for doc in case["required_documents"]}
    assert len(cases) == 60
    assert covered == set(knowledge.document_ids)


def test_eval_v1_has_40_single_and_20_multi_document_cases():
    cases = load_cases()
    assert sum(len(case["required_documents"]) == 1 for case in cases) == 40
    assert sum(len(case["required_documents"]) > 1 for case in cases) == 20


def test_eval_questions_do_not_contain_expected_answer_values():
    for case in load_cases():
        q = case["question"].casefold()
        for value in case["expected_contains"]:
            assert str(value).casefold() not in q, case["id"]


def test_every_expected_value_is_present_in_required_evidence():
    knowledge = KnowledgeBase("corpus/northstar")
    for case in load_cases():
        evidence = "\n".join(knowledge.read(doc).content for doc in case["required_documents"]).casefold()
        for value in case["expected_contains"]:
            assert str(value).casefold() in evidence, (case["id"], value)


def test_case_ids_are_stable_and_unique():
    ids = [case["id"] for case in load_cases()]
    assert len(ids) == len(set(ids))
    assert ids[0] == "EVAL-001"
    assert ids[-1] == "EVAL-060"
