"""LangGraph orchestration: ingest -> extract -> skeptic -+-> counsel -> arbiter.

Why LangGraph over a script: the skeptic's verdict routes the flow —
a failed report skips counseling and goes straight to the arbiter's
abstention gate. That conditional path, plus per-node streaming for the
demo, is exactly what a state machine buys over straight-line code.
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .agents import (arbiter_node, counselor_node, extractor_node,
                     ingest_node, skeptic_node)


class ReportState(TypedDict, total=False):
    report: dict
    normalized: dict
    markers: list
    extraction_confidence: float
    challenges: list
    validated: list
    summary: str | None
    abstained: bool
    abstain_reason: str | None
    answer: str | None
    citations: list
    confidence: float
    dissent: str | None
    ingest_trace: list
    extractor_trace: list
    skeptic_trace: list
    counselor_trace: list
    arbiter_trace: list


def _initial_state(report: dict) -> dict:
    return {"report": report, "summary": None, "abstained": False,
            "abstain_reason": None, "answer": None, "citations": [],
            "confidence": 0.0, "dissent": None}


def build_graph(config, llm):
    """Assemble the pipeline. Nodes close over config/llm."""
    b = StateGraph(ReportState)
    b.add_node("ingest", ingest_node)
    b.add_node("extractor", extractor_node)
    b.add_node("skeptic", skeptic_node)
    b.add_node("counselor", lambda s: counselor_node(s, llm))
    b.add_node("arbiter", lambda s: arbiter_node(s, config))

    b.add_edge(START, "ingest")
    b.add_edge("ingest", "extractor")
    b.add_edge("extractor", "skeptic")

    def route(state: dict) -> str:
        # A report the skeptic already failed needs no counseling prose —
        # route it straight to the arbiter's abstention gate.
        crit = any(c["severity"] == "critical"
                   for c in state.get("challenges", []))
        if crit or state.get("extraction_confidence", 0) == 0:
            return "arbiter"
        return "counselor"

    b.add_conditional_edges("skeptic", route,
                            {"counselor": "counselor", "arbiter": "arbiter"})
    b.add_edge("counselor", "arbiter")
    b.add_edge("arbiter", END)
    return b.compile()


def analyze(report: dict, config, llm) -> dict:
    """Run the full pipeline synchronously; return the final state."""
    return build_graph(config, llm).invoke(_initial_state(report))
