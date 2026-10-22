"""The five Vitalis agents, as LangGraph node functions.

Design rule: safety-critical math (flag recomputation, unit sanity) is
deterministic and rule-based in BOTH mock and real modes. The LLM only
ever writes prose from a structured brief — it never invents a range.

Why a separate skeptic: the extractor reports what the lab PRINTED
(including misprints); the skeptic independently recomputes. Separation
of duties is what catches TRAP-02 style contradictions.
"""
from __future__ import annotations

import re

# Physiologically plausible bounds per (marker, unit): values outside these
# are almost certainly unit mix-ups, not real results.
PLAUSIBLE = {
    ("Glucose", "mg/dL"): (20, 1500),
    ("Potassium", "mmol/L"): (1.5, 9.0),
    ("Sodium", "mmol/L"): (100, 180),
    ("Hemoglobin", "g/dL"): (4.0, 25.0),
    ("Creatinine", "mg/dL"): (0.1, 20.0),
    ("WBC", "K/uL"): (0.1, 150.0),
}

LINE_RE = re.compile(
    r"^([A-Za-z][A-Za-z0-9 /().-]*?)\s*\.+\s*"
    r"([0-9]+(?:\.[0-9]+)?)\s*"
    r"([A-Za-z%/.0-9]*)\s*"
    r"\(([0-9.]+)-([0-9.]+)\)\s*(LOW|HIGH)?\s*$"
)


def recompute_flag(value, lo, hi):
    if value < lo:
        return "low"
    if value > hi:
        return "high"
    return "normal"


def ingest_node(state):
    """Normalize the raw report into a standard dict."""
    trace = []
    rep = state["report"]
    norm = {"report_id": rep["report_id"], "patient": rep["patient"],
            "format": rep["format"]}
    if rep["format"] == "json":
        norm["panels"] = rep.get("panels", [])
        trace.append(f"JSON report: {len(norm['panels'])} panel(s) loaded.")
    else:
        norm["raw_text"] = rep.get("raw_text", "")
        n = len([l for l in norm["raw_text"].splitlines() if "..." in l])
        trace.append(f"Text report: {n} candidate marker line(s) found.")
    return {"normalized": norm, "ingest_trace": trace}


def extractor_node(state):
    """Pull (name, value, unit, range, printed flag) per marker."""
    trace, markers = [], []
    norm = state["normalized"]
    if norm["format"] == "json":
        for p in norm.get("panels", []):
            for m in p["markers"]:
                markers.append({
                    "name": m["name"], "value": m["value"],
                    "unit": m.get("unit"), "ref_low": m["ref_low"],
                    "ref_high": m["ref_high"],
                    "printed_flag": m.get("flag", "normal"),
                    "panel": p["panel"]})
        trace.append(f"Extracted {len(markers)} markers from JSON.")
    else:
        for line in norm.get("raw_text", "").splitlines():
            mt = LINE_RE.match(line.strip())
            if not mt:
                continue
            name, val, unit, lo, hi, flag = mt.groups()
            markers.append({
                "name": name.strip(), "value": float(val),
                "unit": unit or None, "ref_low": float(lo),
                "ref_high": float(hi),
                "printed_flag": (flag or "NORMAL").lower(),
                "panel": "text"})
        trace.append(f"Regex-parsed {len(markers)} markers from text.")
    complete = sum(1 for m in markers
                   if m["name"] and m["value"] is not None and m["unit"]
                   and m["ref_low"] is not None)
    conf = (complete / len(markers)) if markers else 0.0
    trace.append(f"Extraction confidence {conf:.2f} "
                 f"({complete}/{len(markers)} complete).")
    return {"markers": markers, "extraction_confidence": conf,
            "extractor_trace": trace}


def skeptic_node(state):
    """Independently recompute every flag; challenge anything suspicious."""
    challenges, validated = [], []
    for m in state["markers"]:
        issues = []
        if not m["unit"]:
            issues.append(("missing_unit", "critical",
                           f"{m['name']}: unit missing, cannot interpret value"))
        else:
            bounds = PLAUSIBLE.get((m["name"], m["unit"]))
            if bounds and not (bounds[0] <= m["value"] <= bounds[1]):
                issues.append(("implausible_value", "critical",
                               f"{m['name']}: {m['value']} {m['unit']} "
                               f"is physiologically implausible"))
        if m["unit"] and m["ref_low"] is not None:
            recomputed = recompute_flag(m["value"], m["ref_low"], m["ref_high"])
            if recomputed != m["printed_flag"]:
                issues.append(("flag_mismatch", "critical",
                               f"{m['name']}: printed '{m['printed_flag']}' "
                               f"but {m['value']} vs [{m['ref_low']}-"
                               f"{m['ref_high']}] recomputes '{recomputed}'"))
            final_flag = recomputed
        else:
            final_flag = m["printed_flag"]
        for kind, sev, msg in issues:
            challenges.append({"marker": m["name"], "kind": kind,
                               "severity": sev, "message": msg})
        validated.append({**m, "final_flag": final_flag})
    trace = [f"Validated {len(validated)} markers, "
             f"{len(challenges)} challenge(s)."]
    trace += ["! " + c["message"] for c in challenges]
    return {"challenges": challenges, "validated": validated,
            "skeptic_trace": trace}


def counselor_node(state, llm):
    """Draft plain-language summary from validated markers (never raw LLM)."""
    abnormal = [m for m in state["validated"] if m["final_flag"] != "normal"]
    brief = {"total": len(state["validated"]),
             "abnormal": [{"name": m["name"], "value": m["value"],
                           "unit": m["unit"], "flag": m["final_flag"],
                           "ref_low": m["ref_low"], "ref_high": m["ref_high"]}
                          for m in abnormal]}
    import json as _json
    summary = llm.complete(
        "You are a careful health explainer. Summarize lab results plainly. "
        "Use ONLY the numbers in the brief. End with: not medical advice.",
        _json.dumps(brief))
    summary += (" [This is educational information only, not medical advice. "
                "Discuss results with your clinician.]")
    trace = [f"Drafted summary covering {len(abnormal)} abnormal marker(s)."]
    return {"summary": summary, "counselor_trace": trace}


def arbiter_node(state, config):
    """Merge into one cited answer, or abstain via the three gates."""
    challenges = state["challenges"]
    trace = []
    reason = None
    if any(c["kind"] == "missing_unit" for c in challenges):
        n = sum(1 for c in challenges if c["kind"] == "missing_unit")
        reason = f"abstained: {n} marker(s) missing units — unsafe to interpret"
    elif any(c["severity"] == "critical" for c in challenges):
        reason = ("abstained: contradictory or implausible values found — "
                  "the report cannot be trusted as printed")
    elif state["extraction_confidence"] < config.min_extraction_confidence:
        reason = (f"abstained: extraction confidence "
                  f"{state['extraction_confidence']:.2f} below threshold")
    if reason:
        trace.append("GATE TRIGGERED -> " + reason)
        dissent = "; ".join(c["message"] for c in challenges) or None
        return {"abstained": True, "abstain_reason": reason,
                "answer": None, "citations": [], "confidence": 0.0,
                "dissent": dissent, "arbiter_trace": trace}
    abnormal = [m for m in state["validated"] if m["final_flag"] != "normal"]
    citations = [{"marker": m["name"], "panel": m["panel"],
                  "value": f"{m['value']} {m['unit']}",
                  "range": f"{m['ref_low']}-{m['ref_high']}"} for m in abnormal]
    conf = max(0.5, 0.95 - 0.05 * len(
        [c for c in challenges if c["severity"] != "critical"]))
    trace.append(f"Answer approved at confidence {conf:.2f} "
                 f"with {len(citations)} citation(s).")
    return {"abstained": False, "abstain_reason": None,
            "answer": state["summary"], "citations": citations,
            "confidence": conf,
            "dissent": "; ".join(c["message"] for c in challenges) or None,
            "arbiter_trace": trace}
