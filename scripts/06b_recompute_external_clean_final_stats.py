import json
import re
import csv
from pathlib import Path
from collections import Counter

ROOT = Path("/home/tahiti/TimeBound")
INP = ROOT / "converted_external_clean"
STATS = ROOT / "stats"
PAPER = ROOT / "paper_ready"

STATS.mkdir(parents=True, exist_ok=True)
PAPER.mkdir(parents=True, exist_ok=True)

def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9а-яё ,:;./-]+", "", s)
    return s.strip()

def read_jsonl(path):
    rows = []
    bad = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except Exception:
                bad += 1
    return rows, bad

def validate(ex):
    errs = []
    hist = ex.get("history", [])
    gold = ex.get("gold_evidence_turns", [])

    if not ex.get("id"):
        errs.append("missing_id")
    if not ex.get("query"):
        errs.append("missing_query")
    if ex.get("gold_answer") in [None, ""]:
        errs.append("missing_gold_answer")
    if not hist:
        errs.append("empty_history")
    if not gold:
        errs.append("missing_gold_evidence")

    turn_ids = {ev.get("turn_id") for ev in hist}
    for g in gold:
        if g not in turn_ids:
            errs.append("gold_evidence_not_in_history")
            break

    for ev in hist:
        if not ev.get("text"):
            errs.append("memory_missing_text")
        if not ev.get("observation_time"):
            errs.append("missing_observation_time")
        if not ev.get("event_time"):
            errs.append("missing_event_time")
        if not ev.get("valid_from"):
            errs.append("missing_valid_from")
        if not ev.get("status"):
            errs.append("missing_status")

    return sorted(set(errs)) or ["ok"]

def leakage(ex):
    ans = norm(ex.get("gold_answer", ""))
    if not ans or len(ans) < 4:
        return False
    hist = norm(" ".join(ev.get("text", "") for ev in ex.get("history", [])))
    return ans in hist

summary_rows = []
role_rows = []
validation_rows = []
leakage_rows = []

for path in sorted(INP.glob("*_timebound_clean.jsonl")):
    dataset = path.name.replace("_timebound_clean.jsonl", "")
    rows, bad = read_jsonl(path)

    hist_lens = [len(r.get("history", [])) for r in rows]
    ev_lens = [len(r.get("gold_evidence_turns", [])) for r in rows]

    role_counter = Counter(r.get("diagnostic_role", r.get("task_type", "unknown")) for r in rows)
    validation_counter = Counter()
    leaks = 0

    for r in rows:
        for chk in validate(r):
            validation_counter[chk] += 1
        if leakage(r):
            leaks += 1

    summary_rows.append({
        "dataset": dataset,
        "n_examples": len(rows),
        "bad_jsonl_lines": bad,
        "history_min": min(hist_lens) if hist_lens else 0,
        "history_mean": sum(hist_lens) / len(hist_lens) if hist_lens else 0,
        "history_max": max(hist_lens) if hist_lens else 0,
        "gold_evidence_min": min(ev_lens) if ev_lens else 0,
        "gold_evidence_mean": sum(ev_lens) / len(ev_lens) if ev_lens else 0,
        "gold_evidence_max": max(ev_lens) if ev_lens else 0,
        "validation_ok": validation_counter["ok"],
        "validation_non_ok": len(rows) - validation_counter["ok"],
        "answer_leak_examples": leaks,
        "answer_leak_rate": leaks / len(rows) if rows else 0,
        "path": str(path),
    })

    for role, n in role_counter.items():
        role_rows.append({
            "dataset": dataset,
            "diagnostic_role": role,
            "n": n,
            "share": n / len(rows) if rows else 0,
        })

    for chk, n in validation_counter.items():
        validation_rows.append({
            "dataset": dataset,
            "check": chk,
            "n_examples": n,
        })

    leakage_rows.append({
        "dataset": dataset,
        "n_examples": len(rows),
        "answer_leak_examples": leaks,
        "answer_leak_rate": leaks / len(rows) if rows else 0,
    })

def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

summary_fields = [
    "dataset", "n_examples", "bad_jsonl_lines",
    "history_min", "history_mean", "history_max",
    "gold_evidence_min", "gold_evidence_mean", "gold_evidence_max",
    "validation_ok", "validation_non_ok",
    "answer_leak_examples", "answer_leak_rate",
    "path",
]

write_csv(STATS / "external_clean_final_summary.csv", summary_rows, summary_fields)
write_csv(STATS / "external_clean_final_roles.csv", role_rows, ["dataset", "diagnostic_role", "n", "share"])
write_csv(STATS / "external_clean_final_validation.csv", validation_rows, ["dataset", "check", "n_examples"])
write_csv(STATS / "external_clean_final_leakage.csv", leakage_rows, ["dataset", "n_examples", "answer_leak_examples", "answer_leak_rate"])

# Copy to paper_ready
for name in [
    "external_clean_final_summary.csv",
    "external_clean_final_roles.csv",
    "external_clean_final_validation.csv",
    "external_clean_final_leakage.csv",
]:
    src = STATS / name
    dst = PAPER / name
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

# LaTeX table
role_map = {r["dataset"]: r["diagnostic_role"] for r in role_rows}

latex = STATS / "latex_external_clean_final_summary.tex"
with latex.open("w", encoding="utf-8") as f:
    f.write("\\begin{table}[t]\n")
    f.write("\\centering\n")
    f.write("\\small\n")
    f.write("\\begin{tabular}{llrrrr}\n")
    f.write("\\toprule\n")
    f.write("Dataset & Diagnostic role & Examples & Avg. turns & Validated & Leak rate \\\\\n")
    f.write("\\midrule\n")
    for row in summary_rows:
        ds = row["dataset"]
        role = role_map.get(ds, "unknown").replace("_", " ")
        f.write(
            f"{ds} & {role} & "
            f"{row['n_examples']} & "
            f"{row['history_mean']:.1f} & "
            f"{row['validation_ok']} / {row['n_examples']} & "
            f"{row['answer_leak_rate']:.3f} \\\\\n"
        )
    f.write("\\bottomrule\n")
    f.write("\\end{tabular}\n")
    f.write("\\caption{Clean converted external diagnostics in TimeBound-style format. Answer fields are removed from retrieved contexts before evaluation.}\n")
    f.write("\\label{tab:external_clean_final_stats}\n")
    f.write("\\end{table}\n")

(PAPER / "latex_external_clean_final_summary.tex").write_text(
    latex.read_text(encoding="utf-8"),
    encoding="utf-8",
)

print("\n=== External clean final summary ===")
for r in summary_rows:
    print(r)

print("\n=== Leakage ===")
for r in leakage_rows:
    print(r)

print("\nSaved final clean stats to:")
print(STATS / "external_clean_final_summary.csv")
print(STATS / "external_clean_final_roles.csv")
print(STATS / "external_clean_final_validation.csv")
print(STATS / "external_clean_final_leakage.csv")
print(STATS / "latex_external_clean_final_summary.tex")
