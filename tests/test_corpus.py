from pathlib import Path

from progressive_disclosure.knowledge import KnowledgeBase


def test_corpus_has_no_legacy_indexes():
    assert not list(Path("corpus/northstar").rglob("_index.yaml"))


def test_corpus_metadata_is_self_describing():
    kb = KnowledgeBase("corpus/northstar")
    assert len(kb.catalog()) == 40
    for item in kb.catalog():
        assert item.id
        assert item.title
        assert item.description
        assert item.path.endswith(".md")
