"""Loads data/sample/reports.jsonl — synthetic lab reports.

Why JSONL: one report per line streams cleanly and diffs well; each record
is self-contained (report + expected markers + trap label) so eval needs
no second file.
"""
from __future__ import annotations

import json
import os

REQUIRED = {"report_id", "format", "patient", "expected"}


class ReportCorpus:
    def __init__(self, path: str):
        self.path = path
        self.reports = []
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                missing = REQUIRED - set(rec)
                if missing:
                    raise ValueError(f"line {i}: missing {missing}")
                self.reports.append(rec)

    def __len__(self):
        return len(self.reports)

    def get(self, report_id: str) -> dict:
        for r in self.reports:
            if r["report_id"] == report_id:
                return r
        raise KeyError(f"unknown report {report_id}")

    def traps(self):
        return [r for r in self.reports if r.get("trap")]

    def non_traps(self):
        return [r for r in self.reports if not r.get("trap")]

    def marker_count(self) -> int:
        return sum(len(p.get("markers", []))
                   for r in self.reports for p in r.get("panels", []))


def default_corpus() -> ReportCorpus:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return ReportCorpus(os.path.join(root, "data", "sample", "reports.jsonl"))
