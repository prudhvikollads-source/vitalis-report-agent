"""Vitalis live demo: watch five agents read a lab report.

Runs fully offline in mock mode (no API key). The agent floor streams
each LangGraph node's work as it happens — the process IS the demo.
"""
import os
import sys
import time

import streamlit as st
import streamlit.components.v1 as components

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.floor import render_floor
from src.config import Config
from src.corpus import ReportCorpus
from src.graph import _initial_state, build_graph
from src.llm import LLMClient

st.set_page_config(page_title="Vitalis — Clinical Report Intelligence", layout="wide")
st.title("Vitalis — Clinical Report Intelligence Agent")
st.warning("Demo data: 24 synthetic lab reports (fictional patients). "
           "Not medical advice — educational demo only.")

CORPUS = ReportCorpus(os.path.join(ROOT, "data", "sample", "reports.jsonl"))
OPTIONS = [(f"{r['report_id']} — "
            f"{'TRAP: ' + r['trap'] if r.get('trap') else 'routine'}")
           for r in CORPUS.reports]


@st.cache_resource
def load_pipeline():
    cfg = Config()
    cfg.mock = True  # offline demo; set VITALIS_MOCK=false + key for real LLM
    return build_graph(cfg, LLMClient(cfg))


graph = load_pipeline()
choice = st.selectbox("Pick a lab report:", OPTIONS)
rid = choice.split(" — ")[0]
report = CORPUS.get(rid)

STAGES = {
    "ingest": ("📥 IngestAgent", "ingest_trace"),
    "extractor": ("🔬 MarkerExtractor", "extractor_trace"),
    "skeptic": ("🛡️ RangeSkeptic", "skeptic_trace"),
    "counselor": ("💬 Counselor", "counselor_trace"),
    "arbiter": ("⚖️ Arbiter", "arbiter_trace"),
}

if st.button("Analyze report", type="primary"):
    st.subheader("Agent floor — watch the work")
    components.html(render_floor(), height=370)
    with st.expander("Pipeline transcript", expanded=False):
        transcript = st.container()
    final = {}
    for event in graph.stream(_initial_state(report), stream_mode="updates"):
        for node, update in event.items():
            final.update(update)
            label, trace_key = STAGES[node]
            with transcript.expander(f"{label} — done",
                                     expanded=(node == "arbiter")):
                for line in update.get(trace_key, []):
                    st.write(("⚠️ " if line.startswith("!") else "• ") + line)
                if node == "extractor":
                    st.write(f"{len(update.get('markers', []))} markers, "
                             f"confidence "
                             f"{update.get('extraction_confidence', 0):.2f}")
                if node == "skeptic" and update.get("challenges"):
                    st.write(f"{len(update['challenges'])} challenge(s) "
                             f"issued.")
            time.sleep(0.4)
    st.divider()
    if final.get("abstained"):
        st.error(f"**ABSTAINED** — {final.get('abstain_reason')}")
        if final.get("dissent"):
            with st.expander("Why the skeptic refused"):
                st.write(final["dissent"])
        st.info("A wrong health insight is worse than none: Vitalis refused "
                "rather than guess.")
    else:
        st.subheader("Insights")
        st.progress(min(final.get("confidence", 0), 1.0),
                    text=f"confidence {final.get('confidence', 0):.2f}")
        st.write(final.get("answer", ""))
        with st.expander(f"Citations ({len(final.get('citations', []))})"):
            for c in final.get("citations", []):
                st.write(f"• {c['marker']}: {c['value']} "
                         f"(ref {c['range']}) [{c['panel']}]")
        if final.get("dissent"):
            with st.expander("Skeptic notes"):
                st.write(final["dissent"])
    st.caption("Mock mode: deterministic, offline. Set VITALIS_MOCK=false + "
               "VITALIS_API_KEY for a live LLM (prose only; flag math stays "
               "rule-based).")
