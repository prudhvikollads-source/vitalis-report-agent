"""Tests: the skeptic catches what the extractor merely transcribes."""
from src.agents import extractor_node, ingest_node, skeptic_node
from src.corpus import default_corpus


def _skepticked(rid):
    s = {"report": default_corpus().get(rid)}
    s.update(ingest_node(s))
    s.update(extractor_node(s))
    return skeptic_node(s)


def test_clean_report_no_challenges():
    out = _skepticked("RPT-001")
    assert out["challenges"] == []


def test_contradiction_raises_flag_mismatch():
    out = _skepticked("TRAP-02")
    kinds = {c["kind"] for c in out["challenges"]}
    assert "flag_mismatch" in kinds
    pot = [c for c in out["challenges"] if c["marker"] == "Potassium"]
    assert pot and "6.4" in pot[0]["message"]


def test_missing_unit_challenged():
    out = _skepticked("TRAP-01")
    kinds = {c["kind"] for c in out["challenges"]}
    assert "missing_unit" in kinds


def test_implausible_value_challenged():
    out = _skepticked("TRAP-04")
    kinds = {c["kind"] for c in out["challenges"]}
    assert "implausible_value" in kinds


def test_recomputed_flag_corrects_printed():
    out = _skepticked("TRAP-02")
    by_name = {m["name"]: m for m in out["validated"]}
    assert by_name["Potassium"]["final_flag"] == "high"  # printed said normal
