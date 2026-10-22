"""Tests: marker extraction from JSON and text."""
from src.agents import extractor_node, ingest_node
from src.corpus import default_corpus


def _extracted(rid):
    s = {"report": default_corpus().get(rid)}
    s.update(ingest_node(s))
    return extractor_node(s)


def test_json_extraction_complete():
    out = _extracted("RPT-001")
    assert len(out["markers"]) == 6
    assert out["extraction_confidence"] == 1.0
    names = {m["name"] for m in out["markers"]}
    assert "Hemoglobin" in names


def test_text_extraction_parses_values():
    out = _extracted("RPT-013")
    by_name = {m["name"]: m for m in out["markers"]}
    assert by_name["Hemoglobin"]["value"] == 10.1
    assert by_name["Hemoglobin"]["unit"] == "g/dL"
    assert by_name["Hemoglobin"]["printed_flag"] == "low"


def test_text_extraction_confidence_high():
    out = _extracted("RPT-014")
    assert out["extraction_confidence"] >= 0.9


def test_non_lab_text_extracts_nothing():
    out = _extracted("TRAP-03")
    assert out["markers"] == []
    assert out["extraction_confidence"] == 0.0
