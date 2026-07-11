import json
from pathlib import Path
from collections import Counter
import pandas as pd

ROOT = Path("/home/tahiti/TimeBound")
STATS = ROOT / "stats"
STATS.mkdir(parents=True, exist_ok=True)

def read_jsonl(path):
    rows, bad = [], 0
    if not path.exists():
        return rows, bad
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                bad += 1
    return rows, bad

def safe_load_json_count(path):
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(obj, list):
            return len(obj), "list"
        if isinstance(obj, dict):
            # common QA containers
            for k in ["data", "examples", "instances", "questions"]:
                if isinstance(obj.get(k), list):
                    return len(obj[k]), f"dict.{k}"
            return len(obj), "dict.keys"
        return None, type(obj).__name__
    except Exception as e:
        return None, f"error:{type(e).__name__}"

def validate_timebound(ex):
    errors = []
    hist = ex.get("history", [])
    gold = ex.get("gold_evidence_turns", [])

    if not ex.get("id"):
        errors.append("missing_id")
    if not hist:
        errors.append("empty_history")
    if not ex.get("query"):
        errors.append("missing_query")
    if ex.get("gold_answer") in [None, ""]:
        errors.append("missing_gold_answer")
    if not gold:
        errors.append("missing_gold_evidence")

    turn_ids = {ev.get("turn_id") for ev in hist}
    for g in gold:
        if g not in turn_ids:
            errors.append("gold_evidence_not_in_history")
            break

    for ev in hist:
        if not ev.get("text"):
            errors.append("memory_missing_text")
        if not ev.get("observation_time"):
            errors.append("missing_observation_time")
        if not ev.get("event_time"):
            errors.append("missing_event_time")
        if not ev.get("valid_from"):
            errors.append("missing_valid_from")
        if not ev.get("status"):
            errors.append("missing_status")
        vf = ev.get("valid_from")
        vt = ev.get("valid_to")
        if vf and vt and str(vf) > str(vt):
            errors.append("invalid_interval_order")

    return sorted(set(errors)) or ["ok"]

# ---------------- TimeBound synthetic stats ----------------
tb_path = ROOT / "synthetic" / "timebound_long.jsonl"
tb_rows, tb_bad = read_jsonl(tb_path)

summary_rows = []
task_rows = []
status_rows = []
validation_rows = []

if tb_rows:
    hist_lens = [len(r.get("history", [])) for r in tb_rows]
    ev_lens = [len(r.get("gold_evidence_turns", [])) for r in tb_rows]
    task_counter = Counter(r.get("task_type", "unknown") for r in tb_rows)
    status_counter = Counter()
    validation_counter = Counter()

    for r in tb_rows:
        for ev in r.get("history", []):
            status_counter[ev.get("status", "missing")] += 1
        for chk in validate_timebound(r):
            validation_counter[chk] += 1

    summary_rows.append({
        "dataset": "TimeBound-Long",
        "path": str(tb_path),
        "n_examples": len(tb_rows),
        "bad_jsonl_lines": tb_bad,
        "n_task_families": len(task_counter),
        "history_min": min(hist_lens),
        "history_mean": sum(hist_lens) / len(hist_lens),
        "history_max": max(hist_lens),
        "gold_evidence_min": min(ev_lens),
        "gold_evidence_mean": sum(ev_lens) / len(ev_lens),
        "gold_evidence_max": max(ev_lens),
        "validation_ok": validation_counter["ok"],
        "validation_non_ok": len(tb_rows) - validation_counter["ok"],
    })

    for k, v in task_counter.most_common():
        task_rows.append({
            "dataset": "TimeBound-Long",
            "task_family": k,
            "n": v,
            "share": v / len(tb_rows),
        })

    for k, v in status_counter.most_common():
        status_rows.append({
            "dataset": "TimeBound-Long",
            "status": k,
            "n_memory_events": v,
        })

    for k, v in validation_counter.most_common():
        validation_rows.append({
            "dataset": "TimeBound-Long",
            "check": k,
            "n_examples": v,
        })

# ---------------- External raw audit ----------------
external_files = []
for root in [
    ROOT / "data" / "raw" / "TempReason",
    ROOT / "data" / "raw" / "complex-tr",
    ROOT / "data" / "raw" / "TCP",
    ROOT / "data" / "raw" / "locomo" / "data",
]:
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in [".json", ".jsonl"]:
                external_files.append(p)

external_rows = []
for p in sorted(external_files):
    size_mb = p.stat().st_size / (1024 * 1024)
    if p.suffix.lower() == ".jsonl":
        n = 0
        bad = 0
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.strip():
                    n += 1
        container = "jsonl.lines"
    else:
        # Do not fully parse huge complex-tr files above 2GB.
        if size_mb > 2000:
            n, container = None, "too_large_skipped"
        else:
            n, container = safe_load_json_count(p)
        bad = None

    external_rows.append({
        "dataset_root": str(p.relative_to(ROOT / "data" / "raw")).split("/")[0],
        "file": str(p.relative_to(ROOT)),
        "size_mb": round(size_mb, 2),
        "n_records_or_top_items": n,
        "container": container,
    })

pd.DataFrame(summary_rows).to_csv(STATS / "timebound_dataset_summary.csv", index=False)
pd.DataFrame(task_rows).to_csv(STATS / "timebound_task_distribution.csv", index=False)
pd.DataFrame(status_rows).to_csv(STATS / "timebound_status_distribution.csv", index=False)
pd.DataFrame(validation_rows).to_csv(STATS / "timebound_validation_checks.csv", index=False)
pd.DataFrame(external_rows).to_csv(STATS / "external_raw_audit.csv", index=False)

print("\n=== TimeBound summary ===")
print(pd.DataFrame(summary_rows).to_string(index=False))

print("\n=== Task distribution ===")
print(pd.DataFrame(task_rows).to_string(index=False))

print("\n=== Status distribution ===")
print(pd.DataFrame(status_rows).to_string(index=False))

print("\n=== Validation checks ===")
print(pd.DataFrame(validation_rows).to_string(index=False))

print("\n=== External raw audit, first 40 rows ===")
print(pd.DataFrame(external_rows).head(40).to_string(index=False))

print("\nSaved CSVs to:", STATS)
