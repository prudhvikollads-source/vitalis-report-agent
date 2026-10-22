#!/bin/bash
# One-click setup: venv -> deps -> tests -> eval -> sample analysis.
set -e
cd "$(dirname "$0")/.."
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m src.eval
.venv/bin/python -m src.run --report RPT-002
echo "Quickstart green. Run 'make demo' for the live agent floor."
