"""Generate synthetic lab reports (deterministic, seed=42).

Why a generator, not hand-written JSON: 24 reports x ~12 markers is 300+
fields — a seeded generator keeps them consistent (flags match values,
ranges match sex) and reproducible. Traps are hand-specified below.
"""
import json
import os
import random

random.seed(42)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "sample", "reports.jsonl")

DISCLAIMER = "Synthetic demo data. Not medical advice."

# name -> (unit, ref_low_F, ref_high_F, ref_low_M, ref_high_M, mean, sd)
MARKERS = {
    "Hemoglobin": ("g/dL", 12.0, 15.5, 13.5, 17.5, 13.8, 0.9),
    "Hematocrit": ("%", 36.0, 46.0, 41.0, 53.0, 41.0, 2.8),
    "WBC": ("K/uL", 4.5, 11.0, 4.5, 11.0, 7.0, 1.6),
    "Platelets": ("K/uL", 150, 400, 150, 400, 250, 55),
    "MCV": ("fL", 80.0, 100.0, 80.0, 100.0, 90.0, 4.5),
    "RBC": ("M/uL", 3.9, 5.03, 4.32, 5.72, 4.6, 0.35),
    "Glucose": ("mg/dL", 70, 100, 70, 100, 88, 8),
    "Creatinine": ("mg/dL", 0.6, 1.1, 0.7, 1.3, 0.9, 0.15),
    "eGFR": ("mL/min/1.73", 60, 120, 60, 120, 95, 12),
    "Sodium": ("mmol/L", 136, 145, 136, 145, 140, 2.2),
    "Potassium": ("mmol/L", 3.5, 5.1, 3.5, 5.1, 4.2, 0.35),
    "BUN": ("mg/dL", 7, 20, 7, 20, 14, 3.2),
    "Calcium": ("mg/dL", 8.5, 10.5, 8.5, 10.5, 9.4, 0.4),
    "ALT": ("U/L", 7, 56, 7, 56, 24, 9),
    "AST": ("U/L", 10, 40, 10, 40, 22, 6),
    "Albumin": ("g/dL", 3.5, 5.5, 3.5, 5.5, 4.4, 0.35),
    "Total Cholesterol": ("mg/dL", 125, 200, 125, 200, 175, 22),
    "LDL": ("mg/dL", 0, 100, 0, 100, 105, 22),
    "HDL": ("mg/dL", 50, 100, 40, 100, 55, 11),
    "Triglycerides": ("mg/dL", 0, 150, 0, 150, 110, 32),
}

PANELS = {
    "CBC": ["Hemoglobin", "Hematocrit", "WBC", "Platelets", "MCV", "RBC"],
    "Metabolic": ["Glucose", "Creatinine", "eGFR", "Sodium", "Potassium",
                  "BUN", "Calcium", "ALT", "AST", "Albumin"],
    "Lipid": ["Total Cholesterol", "LDL", "HDL", "Triglycerides"],
}


def flag_of(value, lo, hi):
    if value < lo:
        return "low"
    if value > hi:
        return "high"
    return "normal"


def make_marker(name, sex, override=None):
    unit, lo_f, hi_f, lo_m, hi_m, mean, sd = MARKERS[name]
    lo, hi = (lo_f, hi_f) if sex == "F" else (lo_m, hi_m)
    value = override if override is not None else round(random.gauss(mean, sd), 1)
    if name == "Creatinine":
        value = round(value, 2)
    return {"name": name, "value": value, "unit": unit,
            "ref_low": lo, "ref_high": hi, "flag": flag_of(value, lo, hi)}


def to_text(rec):
    """Render a report as a realistic lab printout."""
    lines = ["ST. MERCY LABORATORY", f"Collected: {rec['collected']}",
             f"Patient: {rec['patient']['id']} "
             f"({rec['patient']['sex']}, {rec['patient']['age']}y)", ""]
    for panel in rec["panels"]:
        lines.append(panel["panel"].upper())
        for m in panel["markers"]:
            flag = {"low": "LOW", "high": "HIGH", "normal": ""}[m["flag"]]
            unit = m["unit"] if m["unit"] else ""
            lines.append(f"{m['name']} {'.' * (22 - len(m['name']))} "
                         f"{m['value']} {unit} "
                         f"({m['ref_low']}-{m['ref_high']}) {flag}".rstrip())
        lines.append("")
    return "\n".join(lines)


def build(report_id, sex, age, panels, overrides=None, fmt="json"):
    overrides = overrides or {}
    pid = f"PX-{1000 + int(report_id.split('-')[1])}"
    rec = {"report_id": report_id, "format": fmt,
           "patient": {"id": pid, "age": age, "sex": sex},
           "collected": f"2026-{random.randint(1, 9):02d}-{random.randint(1, 28):02d}",
           "panels": [], "trap": None, "synthetic": True,
           "disclaimer": DISCLAIMER}
    for panel in panels:
        markers = [make_marker(n, sex, overrides.get(n)) for n in PANELS[panel]]
        rec["panels"].append({"panel": panel, "markers": markers})
    if fmt == "text":
        rec["raw_text"] = to_text(rec)
    rec["expected"] = {
        "abstain": False,
        "markers": [{"name": m["name"], "flag": m["flag"]}
                    for p in rec["panels"] for m in p["markers"]],
    }
    return rec


def main():
    R = []
    R.append(build("RPT-001", "F", 34, ["CBC"]))
    R.append(build("RPT-002", "F", 52, ["CBC"],
                   {"Hemoglobin": 10.1, "Hematocrit": 31.2, "MCV": 76.4}))
    R.append(build("RPT-003", "M", 45, ["CBC"], {"WBC": 14.2}))
    R.append(build("RPT-004", "F", 61, ["CBC"], {"Platelets": 98}))
    R.append(build("RPT-005", "M", 38, ["Metabolic"]))
    R.append(build("RPT-006", "F", 57, ["Metabolic"], {"Glucose": 118}))
    R.append(build("RPT-007", "M", 66, ["Metabolic"],
                   {"Creatinine": 1.9, "eGFR": 38, "BUN": 28}))
    R.append(build("RPT-008", "F", 49, ["Metabolic"], {"Potassium": 5.9}))
    R.append(build("RPT-009", "M", 53, ["Metabolic"],
                   {"ALT": 128, "AST": 96}))
    R.append(build("RPT-010", "F", 44, ["Lipid"]))
    R.append(build("RPT-011", "M", 59, ["Lipid"], {"LDL": 178}))
    R.append(build("RPT-012", "F", 63, ["Lipid"],
                   {"Triglycerides": 312, "HDL": 38}))
    R.append(build("RPT-013", "F", 52, ["CBC"],
                   {"Hemoglobin": 10.1, "Hematocrit": 31.2}, fmt="text"))
    R.append(build("RPT-014", "M", 47, ["Metabolic"], {"Sodium": 131},
                   fmt="text"))
    R.append(build("RPT-015", "F", 36, ["Lipid"], fmt="text"))
    R.append(build("RPT-016", "M", 58, ["CBC", "Metabolic", "Lipid"],
                   {"LDL": 164, "Glucose": 109, "WBC": 11.8}))
    R.append(build("RPT-017", "F", 71, ["CBC", "Metabolic"],
                   {"Hemoglobin": 11.4, "eGFR": 58, "Potassium": 5.3}))
    R.append(build("RPT-018", "M", 42, ["Metabolic", "Lipid"], fmt="text"))
    r = build("RPT-019", "F", 55, ["Metabolic"],
              {"Sodium": 136, "Potassium": 5.1, "Glucose": 100})
    R.append(r)  # borderline values, all normal
    R.append(build("RPT-020", "M", 50, ["CBC"], {"MCV": 101.2}))

    # ---- Traps (hand-specified) ----
    t1 = build("TRAP-01", "F", 40, ["CBC", "Metabolic"])
    for p in t1["panels"]:
        for m in p["markers"][:3]:
            m["unit"] = None  # missing units -> Gate 1
    t1["trap"] = "missing_units"
    t1["expected"] = {"abstain": True, "markers": []}
    R.append(t1)

    t2 = build("TRAP-02", "M", 62, ["Metabolic"],
               {"Potassium": 6.4, "Creatinine": 2.4, "Glucose": 210})
    for p in t2["panels"]:  # lab mis-printed flags as normal
        for m in p["markers"]:
            if m["flag"] != "normal":
                m["flag"] = "normal"
    t2["trap"] = "contradiction"
    t2["expected"] = {"abstain": True, "markers": []}
    R.append(t2)

    t3 = {"report_id": "TRAP-03", "format": "text",
          "patient": {"id": "PX-1099", "age": 58, "sex": "M"},
          "collected": "2026-07-02", "panels": [], "trap": "non_lab",
          "synthetic": True, "disclaimer": DISCLAIMER,
          "raw_text": ("DISCHARGE SUMMARY\nPatient tolerated procedure well. "
                       " ambulated this morning, appetite fair. Follow up "
                       "with cardiology in two weeks. Prescriptions sent to "
                       "pharmacy."),
          "expected": {"abstain": True, "markers": []}}
    R.append(t3)

    t4 = build("TRAP-04", "F", 45, ["Metabolic"], {"Glucose": 5.4})
    # 5.4 mg/dL glucose is physiologically implausible -> unit mismatch
    t4["trap"] = "unit_mismatch"
    t4["expected"] = {"abstain": True, "markers": []}
    R.append(t4)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        for rec in R:
            f.write(json.dumps(rec) + "\n")
    n_markers = sum(len(p["markers"]) for r in R for p in r.get("panels", []))
    print(f"Wrote {len(R)} reports, {n_markers} markers -> {OUT}")


if __name__ == "__main__":
    main()
