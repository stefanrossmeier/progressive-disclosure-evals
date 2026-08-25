from evals.grading import answer_matches_expected, expected_value_matches


def test_how_many_grading_accepts_concise_word_count_without_repeated_noun():
    assert answer_matches_expected(
        "Five.",
        ["five resurfacing episodes"],
        question="How many distinct resurfacing episodes were recognized?",
    )


def test_how_many_grading_accepts_numeric_and_word_equivalence():
    assert expected_value_matches(
        "Seventeen.",
        "17 socketed arrowheads",
        question="How many socketed arrowheads were included in the hoard?",
    )
    assert expected_value_matches(
        "31.",
        "31 graves",
        question="How many graves were excavated?",
    )
    assert expected_value_matches(
        "Six.",
        "Six doorways",
        question="How many doorways opened directly onto the courtyard?",
    )


def test_count_shortcut_does_not_weaken_non_count_questions():
    assert not expected_value_matches(
        "17.",
        "17 socketed arrowheads",
        question="Which artefacts were included in the hoard?",
    )


def test_multi_fact_how_many_case_still_requires_non_count_value():
    question = (
        "Which sampled courtyard deposit produced the youngest radiocarbon median, "
        "and how many resurfacings overlay the original pavement there?"
    )
    assert answer_matches_expected(
        "Aster-RC-204; five.",
        ["Aster-RC-204", "five resurfacing episodes"],
        question=question,
    )
    assert not answer_matches_expected(
        "Five.",
        ["Aster-RC-204", "five resurfacing episodes"],
        question=question,
    )


def test_semantic_grading_does_not_require_noun_already_in_question():
    question = "What material was used for the inlay of SF-132?"
    assert expected_value_matches("Shell.", "shell inlay", question=question)
    assert not expected_value_matches("Ivory.", "shell inlay", question=question)
