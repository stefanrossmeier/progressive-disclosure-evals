from __future__ import annotations

import re
from collections.abc import Iterable


_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def normalize_match_text(value: str) -> str:
    folded = value.casefold().replace("–", "-").replace("—", "-")
    folded = re.sub(
        r"\b(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\s*utc\b",
        r"\1 utc - \2 utc",
        folded,
    )
    folded = re.sub(r"(?<=\d)\s*(?:percent|per cent|%)", "%", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", folded)


def _canonical_number(token: str) -> int | None:
    token = token.casefold().strip(".,;:()[]{}")
    if token.isdigit():
        return int(token)
    if token in _NUMBER_WORDS:
        return _NUMBER_WORDS[token]
    if "-" in token:
        left, right = token.split("-", 1)
        if left in _NUMBER_WORDS and right in _NUMBER_WORDS:
            left_value = _NUMBER_WORDS[left]
            right_value = _NUMBER_WORDS[right]
            if left_value >= 20 and left_value % 10 == 0 and 0 < right_value < 10:
                return left_value + right_value
    return None


def _leading_count(value: str) -> int | None:
    normalized = normalize_match_text(value)
    match = re.match(r"^([a-z]+(?:-[a-z]+)?|\d+)\b", normalized)
    if not match:
        return None
    return _canonical_number(match.group(1))


def _answer_contains_count(answer: str, count: int) -> bool:
    normalized = normalize_match_text(answer)
    for token in re.findall(r"[a-z]+(?:-[a-z]+)?|\d+", normalized):
        if _canonical_number(token) == count:
            return True
    return False


def expected_value_matches(answer: str, value: str, *, question: str = "") -> bool:
    answer_folded = normalize_match_text(answer)
    normalized = normalize_match_text(value)
    if normalized in answer_folded:
        return True

    # For a question that explicitly asks "how many", grade the requested count rather
    # than requiring the answer to repeat the noun phrase already supplied by the question.
    # Keep the richer expected phrase in the dataset so global metadata-leakage checks stay meaningful.
    if re.search(r"\bhow many\b", question, flags=re.IGNORECASE):
        count = _leading_count(value)
        if count is not None and _answer_contains_count(answer, count):
            return True

    aliases = {"inside": "within"}
    generic = {
        "source",
        "individual",
        "individuals",
        "numeral",
        "ceramic",
        "object",
        "context",
        "sample",
    }
    expected_tokens = [
        aliases.get(token, token)
        for token in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", normalized)
    ]
    answer_tokens = {
        aliases.get(token, token)
        for token in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", answer_folded)
    }
    question_tokens = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", normalize_match_text(question)))
    # Do not require the answer to repeat generic nouns already supplied by the question.
    # Example: for "What material was used for the inlay?" the gold phrase "shell inlay"
    # should accept the concise answer "Shell." while still requiring the distinctive value.
    distinctive = [
        token for token in expected_tokens
        if token not in generic and token not in question_tokens
    ]
    return bool(distinctive) and all(token in answer_tokens for token in distinctive)


def answer_matches_expected(
    answer: str,
    expected_values: Iterable[str],
    *,
    question: str = "",
) -> bool:
    return all(expected_value_matches(answer, value, question=question) for value in expected_values)
