# Vitalis — Clinical Report Intelligence Agent

![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-2E7D32)
![Streamlit](https://img.shields.io/badge/Streamlit-live%20demo-FF4B4B?logo=streamlit)
![pytest](https://img.shields.io/badge/pytest-18%20tests-0A9EDC)
![License](https://img.shields.io/badge/License-MIT-green)

> **Live demo:** `streamlit run app/streamlit_demo.py` — watch five agents read a lab report live · **Case study:** [`docs/index.html`](docs/index.html) (GitHub Pages-ready)

> ⚠️ **Demo data disclaimer:** all 24 lab reports are synthetic with fictional patients, generated for software demonstration only. **Not medical advice.** The agent is a software demo, not a medical device.

## Problem statement

Patients and clinicians drown in lab reports. The default today is pasting a report into a single LLM call — which hallucinates reference ranges and **never says "I don't know."**

Measured on this repo's corpus (`python -m src.eval`, 24 synthetic reports, 208 markers): a naive single-pass baseline (trust the lab's pre-printed flags, no validation, never abstains) returns confident answers on **100% of adversarial reports** — including reporting **"normal" on 3 critically abnormal values** (potassium 6.4 mmol/L among them). Every one of those answers would need manual re-verification against the ranges, and the confident wrong ones are the dangerous ones.

## Solution summary

Five specialist agents on LangGraph read the report in stages: **Ingest** normalizes it, **Extractor** pulls biomarkers, **Skeptic** independently recomputes every flag and challenges contradictions, **Counselor** drafts plain-language insights, and **Arbiter** merges them into one cited answer — or **abstains** via three independent gates. Safety-critical flag math is rule-based in every mode; the LLM only writes prose from a structured brief.

## Business impact

| | Before (single LLM call) | After (Vitalis) |
|---|---|---|
| Trap abstention (4 adversarial reports) | 0% — always answers | **100%** — refuses all 4 |
| Dangerously mis-flagged critical values | 3 reported "normal" | **0** |
| Flag accuracy (20 routine reports) | 1.000 | 1.000 |
| False abstentions (routine reports) | 0 | **0** |
| Extraction F1 (208 markers) | n/a | **1.000** |
| Answer traceability | none | every claim cited to [marker · range] |

## Architecture

```
                    ┌─────────────┐
                    │ IngestAgent │  normalize json / text
                    └──────┬──────┘
                    ┌──────▼──────┐
                    │  Extractor  │  markers + extraction confidence
                    └──────┬──────┘
                    ┌──────▼──────┐
                    │   Skeptic   │  recompute flags, unit sanity
                    └──┬──────┬───┘
              failed │  │ passed
            ┌────────▼──▼──┐  ┌────▼────────┐
            │   Arbiter   │◄─┤  Counselor  │  plain-language draft
            │ (3 gates)   │  └─────────────┘
            └──────┬──────┘
        ┌─────────▼──────────┐
        │ cited answer       │
        │ or ABSTAIN (exit 2)│
        └────────────────────┘
```

The skeptic's verdict routes the flow: a failed report skips counseling and goes straight to the arbiter's abstention gate. Every node streams its trace, which is what the live demo visualizes.

## Key engineering decisions

1. **LangGraph, not LangChain chains.** *Why:* the pipeline is stateful with conditional routing (skeptic failure skips counseling) and per-node streaming. A graph makes each stage inspectable — which is exactly what the demo shows.
2. **A separate skeptic agent.** *Why:* the extractor transcribes what the lab *printed*, misprints included. Only an independent recomputation catches a "normal" flag on potassium 6.4. Separation of duties beats one bigger prompt.
3. **Abstention as a first-class output (exit code 2).** *Why:* in health, a wrong answer is worse than no answer. Three independent gates (missing units / critical contradiction / low extraction confidence) make "I don't know" a designed behavior. Measured: 4/4 traps refused, 0 false refusals.
4. **Rule-based flag math in both modes.** *Why:* an LLM must never invent a reference range. The model only writes prose from a structured brief of already-validated numbers — in mock mode and real mode alike.
5. **Deterministic mock LLM by default.** *Why:* demo, tests, and eval run offline with zero keys and zero cost, reproducibly. Real mode swaps only the prose generator.
6. **Synthetic multi-panel corpus with traps.** *Why:* CBC + metabolic + lipid (not just blood work), plus 4 adversarial reports, keeps the demo honest and safe while exercising every gate.

## How this differs from hia

Inspired by [harshhh28/hia](https://github.com/harshhh28/hia) (LangChain blood-report agent, 235★). Deliberate differences:

| hia | Vitalis |
|---|---|
| LangChain chains | LangGraph with conditional routing + streaming |
| Blood reports only | CBC + metabolic + lipid panels, json + text |
| No abstention concept | 3-gate abstention, measured 100% trap refusal |
| No eval harness | Extraction F1 + flag accuracy + baseline comparison |
| Answer-only demo | Agent-floor demo: watch all five agents work |

## Project structure

```
├── src/
│   ├── __init__.py        # package marker + version
│   ├── config.py          # env/CLI config (mock, model, thresholds)
│   ├── corpus.py          # reports.jsonl loader + validation
│   ├── llm.py             # mock (deterministic) + real LLM via urllib
│   ├── agents.py          # 5 agents: ingest/extract/skeptic/counsel/arbiter
│   ├── graph.py           # LangGraph: conditional skeptic routing
│   ├── eval.py            # Vitalis vs naive baseline, measured metrics
│   └── run.py             # CLI: analyze one report (exit 2 = abstain)
├── app/
│   ├── floor.py           # animated agent floor (canvas, 5 avatars)
│   └── streamlit_demo.py  # live demo: picker, floor, cited answer/abstain
├── data/sample/
│   └── reports.jsonl      # 24 synthetic reports (20 routine + 4 traps)
├── tests/                 # 18 pytest: ingest/extract/skeptic/abstain
├── docs/index.html        # case-study page (GitHub Pages-ready)
├── scripts/
│   ├── generate_reports.py# seeded corpus generator (reproducible)
│   └── quickstart.sh      # one-click setup
├── .github/workflows/ci.yml
├── Dockerfile
└── requirements.txt       # langgraph, streamlit, pytest
```

## Quickstart

```bash
git clone https://github.com/prudhvikollads-source/vitalis-report-agent
cd vitalis-report-agent
bash scripts/quickstart.sh   # venv -> deps -> tests -> eval -> sample run
make demo                    # live agent floor at localhost:8501
```

Manual path:

```bash
pip install -r requirements.txt
pytest tests/ -q              # 18 tests
python -m src.eval            # measured metrics table
python -m src.run --report RPT-002
python -m src.run --report TRAP-02; echo "exit=$?"   # abstains, exit 2
```

## What I'd do differently at scale

- **Real report ingestion:** plug in PDF/OCR (pdfplumber) and HL7/FHIR feeds in the IngestAgent; the graph doesn't change.
- **Reference-range service:** replace in-report ranges with an age/sex-aware range API; the skeptic already recomputes, so it just gets better inputs.
- **Longitudinal tracking:** persist validated markers per patient and add a TrendWatcher agent (delta alerts across reports).
- **Human-in-the-loop:** route low-confidence answers to clinician review queues instead of a binary answer/abstain.
- **Model eval:** swap the mock counselor for a real LLM and grade prose quality with an LLM judge — flag math stays rule-based regardless.

## Demo

The Streamlit app (`make demo`) is the centerpiece:

- **Animated agent floor** — five avatars walk between desks as the pipeline runs: ingest normalizes, extractor pulls markers, the skeptic fires ✉️ challenges, counselor drafts, arbiter adjudicates.
- **Report picker** — 24 reports including 4 traps; pick `TRAP-02` to watch the skeptic catch mis-printed flags and the arbiter refuse.
- **Cited answer card** — plain-language insights with [marker · range] citations, confidence meter, skeptic notes.
- **Abstain banner** — the designed "I don't know," with the reason and the challenges that triggered it.
- **Zero setup** — fully offline in mock mode.

Deploy: [![Streamlit](https://static.streamlit.io/badges/streamlit_badge.svg)](https://share.streamlit.io/) — point it at `app/streamlit_demo.py`. Case study: enable GitHub Pages on `docs/`.

## Maps to your profiles

- **Data Engineer:** document ingestion pipeline (messy text → validated schema), JSONL corpus design, deterministic data generation.
- **Data Scientist:** eval methodology (extraction F1, flag accuracy, abstention rates), trap-based error analysis against a defined baseline.
- **AI Engineer:** LangGraph orchestration with conditional routing, streaming observability, mock/real LLM swap with safety invariants.
- **Product Manager:** problem quantified in harm-avoided terms, impact table, abstention shipped as a product decision — not a failure mode.
