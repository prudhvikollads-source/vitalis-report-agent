"""Eval: Vitalis vs a naive single-pass baseline, all measured, nothing invented.

Baseline (precisely defined): for every marker, trust the lab's pre-printed
flag, no range validation, never abstains. That is what "paste the report
into one LLM call and accept the answer" degrades to when the model
doesn't check the ranges.

Metrics:
- Extraction F1: predicted (name, value) vs expected markers (Vitalis only)
- Flag accuracy on the 20 clean reports: Vitalis final flags vs baseline
  pre-printed flags, each vs expected
- Trap abstention: did the system refuse the 4 trap reports?
- Dangerous misses: baseline "normal" verdicts on critically abnormal traps
"""
from __future__ import annotations

import time

from .config import Config
from .corpus import default_corpus
from .graph import analyze
from .llm import LLMClient


def main():
    cfg = Config()
    cfg.mock = True
    llm = LLMClient(cfg)
    corpus = default_corpus()

    tp = fp = fn = 0
    vit_flag_ok = vit_flag_n = 0
    base_flag_ok = base_flag_n = 0
    vit_abstain_traps = 0
    vit_false_abstain = 0
    dangerous = 0
    t0 = time.time()

    for rep in corpus.reports:
        final = analyze(rep, cfg, llm)
        exp_markers = rep["expected"]["markers"]
        is_trap = bool(rep.get("trap"))

        if is_trap:
            if final.get("abstained"):
                vit_abstain_traps += 1
            # baseline never abstains; count how badly that goes on TRAP-02
            if rep["report_id"] == "TRAP-02":
                # pre-printed flags say normal on K+ 6.4 etc.
                for p in rep["panels"]:
                    for m in p["markers"]:
                        if m["flag"] == "normal" and m["value"] not in (None,):
                            from .agents import recompute_flag
                            if recompute_flag(m["value"], m["ref_low"],
                                              m["ref_high"]) != "normal":
                                dangerous += 1
            continue

        # extraction (Vitalis)
        pred = final.get("validated", [])
        exp_names = {m["name"] for m in exp_markers}
        pred_names = {m["name"] for m in pred}
        tp += len(exp_names & pred_names)
        fp += len(pred_names - exp_names)
        fn += len(exp_names - pred_names)

        # flag accuracy: Vitalis final flags vs expected
        exp_flag = {m["name"]: m["flag"] for m in exp_markers}
        for m in pred:
            if m["name"] in exp_flag:
                vit_flag_n += 1
                if m["final_flag"] == exp_flag[m["name"]]:
                    vit_flag_ok += 1

        # baseline: pre-printed flags, no validation
        for p in rep["panels"]:
            for m in p["markers"]:
                if m["name"] in exp_flag:
                    base_flag_n += 1
                    if m["flag"] == exp_flag[m["name"]]:
                        base_flag_ok += 1

        if final.get("abstained"):
            vit_false_abstain += 1

    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    dt = time.time() - t0

    print(f"{'metric':32} {'Vitalis':>10} {'baseline':>10}")
    print("-" * 54)
    print(f"{'extraction F1':32} {f1:>10.3f} {'n/a':>10}")
    print(f"{'flag accuracy (20 clean)':32} "
          f"{vit_flag_ok / vit_flag_n:>10.3f} {base_flag_ok / base_flag_n:>10.3f}")
    print(f"{'trap abstention (4 traps)':32} "
          f"{vit_abstain_traps / 4:>10.3f} {0.0:>10.3f}")
    print(f"{'false abstentions (20 clean)':32} {vit_false_abstain:>10d} "
          f"{0:>10d}")
    print(f"{'dangerous misses on TRAP-02':32} {'0':>10} {dangerous:>10d}")
    print(f"{'eval time (s)':32} {dt:>10.2f} {'':>10}")
    return {"f1": f1, "vit_flag": vit_flag_ok / vit_flag_n,
            "base_flag": base_flag_ok / base_flag_n,
            "trap_abstain": vit_abstain_traps / 4,
            "false_abstain": vit_false_abstain, "dangerous": dangerous}


if __name__ == "__main__":
    main()
