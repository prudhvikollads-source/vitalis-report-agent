"""Tests: the arbiter abstains on traps, answers clean reports."""
from src.config import Config
from src.corpus import default_corpus
from src.graph import analyze
from src.llm import LLMClient

CFG = Config()
LLM = LLMClient(CFG)


def _analyze(rid):
    return analyze(default_corpus().get(rid), CFG, LLM)


def test_trap_missing_units_abstains():
    out = _analyze("TRAP-01")
    assert out["abstained"] and "unit" in out["abstain_reason"]


def test_trap_contradiction_abstains():
    out = _analyze("TRAP-02")
    assert out["abstained"] and "contradictory" in out["abstain_reason"]


def test_trap_non_lab_abstains():
    out = _analyze("TRAP-03")
    assert out["abstained"]


def test_trap_unit_mismatch_abstains():
    out = _analyze("TRAP-04")
    assert out["abstained"]


def test_clean_report_answered_with_citations():
    out = _analyze("RPT-002")  # anemia panel
    assert not out["abstained"]
    assert out["confidence"] >= 0.5
    cited = {c["marker"] for c in out["citations"]}
    assert "Hemoglobin" in cited  # abnormal -> cited
    assert "not medical advice" in out["answer"]


def test_clean_text_report_answered():
    out = _analyze("RPT-013")
    assert not out["abstained"]
    assert out["answer"]
