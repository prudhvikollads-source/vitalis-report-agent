"""Tests: ingestion normalizes JSON and text reports."""
from src.agents import ingest_node
from src.corpus import default_corpus


def _state(rid):
    return {"report": default_corpus().get(rid)}


def test_ingest_json_counts_panels():
    out = ingest_node(_state("RPT-001"))
    assert len(out["normalized"]["panels"]) == 1
    assert out["ingest_trace"]


def test_ingest_text_counts_lines():
    out = ingest_node(_state("RPT-013"))
    assert out["normalized"]["format"] == "text"
    assert "candidate marker" in out["ingest_trace"][0]


def test_ingest_preserves_patient():
    out = ingest_node(_state("RPT-005"))
    assert out["normalized"]["patient"]["id"].startswith("PX-")
