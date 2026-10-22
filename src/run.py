"""CLI: analyze one report, print cited insights (exit 2 on abstain).

Why exit 2: abstention is a designed outcome callers can branch on —
a wrong health insight is worse than no insight.
"""
from __future__ import annotations

import sys

from .config import Config
from .corpus import default_corpus
from .graph import analyze
from .llm import LLMClient


def main(argv=None) -> int:
    cfg = Config.from_args(argv)
    cfg.validate()
    corpus = default_corpus()
    rid = getattr(cfg, "report_arg", None) or corpus.reports[0]["report_id"]
    report = corpus.get(rid)
    print(f"Analyzing {rid} ({report['format']} format) ...")
    final = analyze(report, cfg, LLMClient(cfg))
    if final.get("abstained"):
        print(f"\nABSTAINED: {final['abstain_reason']}")
        if final.get("dissent"):
            print(f"Skeptic notes: {final['dissent']}")
        return 2
    print(f"\nConfidence: {final['confidence']:.2f}\n")
    print(final["answer"])
    print(f"\nCitations ({len(final['citations'])}):")
    for c in final["citations"]:
        print(f"  - {c['marker']}: {c['value']} (ref {c['range']})")
    if final.get("dissent"):
        print(f"\nSkeptic notes: {final['dissent']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
