from pathlib import Path

from progressive_disclosure.corpora import get_corpus_spec
from progressive_disclosure.knowledge import KnowledgeBase
from scripts.validate_corpus import validate_corpus


def test_registered_corpora_have_no_legacy_indexes_and_validate():
    for name in ("northstar", "tell-aster"):
        spec = get_corpus_spec(name)
        assert not list(spec.root.rglob("_index.yaml"))
        errors, stats = validate_corpus(spec.root, spec)
        assert errors == []
        assert stats.documents == spec.expected_documents


def test_registered_corpora_metadata_is_self_describing():
    for name in ("northstar", "tell-aster"):
        spec = get_corpus_spec(name)
        kb = KnowledgeBase(spec.root)
        assert len(kb.catalog()) == spec.expected_documents
        for item in kb.catalog():
            assert item.id
            assert item.title
            assert item.description
            assert item.path.endswith(".md")


def test_northstar_still_uses_path_derived_ids_as_a_corpus_convention():
    spec = get_corpus_spec("northstar")
    kb = KnowledgeBase(spec.root)
    for item in kb.catalog():
        assert item.id == ".".join(Path(item.path).with_suffix("").parts)


def test_tell_aster_metadata_exposes_question_known_entity_anchors_without_answer_values():
    kb = KnowledgeBase(get_corpus_spec("tell-aster").root)
    expected_anchors = {
        "TA-EXC-04": "SF-241",
        "TA-EXC-07": "W-91",
        "TA-EXC-08": "SF-088",
        "TA-CER-03": "blue-slipped",
        "TA-CER-08": "chronology synthesis",
        "TA-INS-02": "D-44",
        "TA-BUR-06": "B-23",
        "TA-DAT-05": "OSL-6",
        "TA-ARC-07": "western-side plastered storage bins",
        "TA-DAT-03": "modelled or absolute date range",
        "TA-CON-04": "named legacy object -> historical",
        "TA-EXC-03": "Floor F-44",
        "TA-EXC-06": "original excavation interpretation",
        "TA-SYN-04": "not for establishing the original field label",
        "TA-SYN-05": "broad absolute date range",
    }
    by_id = {item.id: item for item in kb.catalog()}
    for document_id, anchor in expected_anchors.items():
        assert anchor in by_id[document_id].description

    catalog_text = "\n".join(item.description for item in kb.catalog())
    for hidden_answer in (
        "412.37 m",
        "3–5 cm",
        "numeral 27",
        "6.5–7.5 years",
        "Type IF-12",
        "F-41",
        "L-77",
        "Ceramic Horizon IV",
        "C-318",
        "1968 season",
    ):
        assert hidden_answer not in catalog_text
