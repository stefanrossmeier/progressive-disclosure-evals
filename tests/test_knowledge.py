from pathlib import Path

import pytest

from progressive_disclosure.knowledge import InvalidCorpusError, KnowledgeBase, UnknownDocumentError


CORPUS = Path("corpus/northstar-corpus")


def test_catalog_contains_all_40_documents():
    kb = KnowledgeBase(CORPUS)
    assert len(kb.catalog()) == 40
    assert len(kb.document_ids) == 40


def test_catalog_exposes_metadata_but_not_leaf_facts():
    kb = KnowledgeBase(CORPUS)
    migration = next(x for x in kb.catalog() if x.id == "commercial.billing.credits.migration")
    assert migration.title == "Migration Credits"
    assert "migration" in migration.description.lower()
    assert migration.path == "commercial/billing/credits/migration.md"
    catalog_text = "\n".join(f"{x.id} {x.title} {x.description}" for x in kb.catalog())
    assert "SABLE-88" not in catalog_text
    assert "17.3" not in catalog_text


def test_read_loads_full_document_and_detects_references():
    kb = KnowledgeBase(CORPUS)
    doc = kb.read("commercial.billing.credits.migration")
    assert "MIG-2" in doc.content
    assert "VIOLET" in doc.content
    assert "SABLE-88" in doc.content
    assert "governance.regions.eu.billing-overrides" in doc.references


def test_unknown_document_raises_clear_error():
    kb = KnowledgeBase(CORPUS)
    with pytest.raises(UnknownDocumentError):
        kb.read("does.not.exist")


def test_missing_corpus_fails(tmp_path):
    with pytest.raises(InvalidCorpusError, match="does not exist"):
        KnowledgeBase(tmp_path / "missing")


def test_document_ids_are_metadata_not_path_conventions(tmp_path):
    path = tmp_path / "a" / "b"
    path.mkdir(parents=True)
    (path / "c.md").write_text(
        "---\nid: stable-external-id\ntitle: T\ndescription: D\n---\nbody\n",
        encoding="utf-8",
    )
    kb = KnowledgeBase(tmp_path)
    assert kb.document_ids == ("stable-external-id",)


def test_tell_aster_catalog_loads_with_non_path_ids_and_optional_versions():
    kb = KnowledgeBase("corpus/tell-aster")
    assert len(kb.document_ids) == 80
    assert "TA-EXC-01" in kb
    assert "14 cm" in kb.read("TA-EXC-01").content


def test_context_size_metrics_are_positive():
    kb = KnowledgeBase(CORPUS)
    assert kb.catalog_characters > 0
    assert kb.full_content_characters > kb.catalog_characters
