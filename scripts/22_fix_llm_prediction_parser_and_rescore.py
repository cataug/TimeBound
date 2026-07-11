import csv
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/tahiti/TimeBound")
OUT = ROOT / "outputs" / "suite82"
STATS = ROOT / "stats"
TABLES = ROOT / "tables"

ROLE_RE = re.compile(r"^(assistant|user|system)\s*[:：]?\s*$", re.I)
ROLE_PREFIX_RE = re.compile(r"^(assistant|user|system)\s*[:：]?\s*", re.I)

def read_jsonl(path):
    rows = []
    if not Path(path).exists():
        return rows
    with Path(path).open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
    return rows

def write_jsonl(path, rows):
    with Path(path).open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

def normalize_answer(s):
    s = str(s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^a-z0-9а-яё ,:;./\-\+]+", "", s)
    s = s.strip(" .,:;")
    return s

def exact_match(pred, gold):
    return int(normalize_answer(pred) == normalize_answer(gold))

def relaxed_match(pred, gold):
    p = normalize_answer(pred)
    g = normalize_answer(gold)

    if not p or not g:
        return 0

    if p == g:
        return 1

    if len(g) >= 3 and g in p:
        return 1

    if len(p) >= 3 and p in g:
        return 1

    # dates/times
    date_re = r"\b\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?\b"
    g_dates = re.findall(date_re, g)
    if g_dates and all(d in p for d in g_dates):
        return 1

    # short categorical answers
    if len(g.split()) <= 3 and g in p:
        return 1

    # yes/no/cancelled/scheduled
    g_yes = g in {"yes", "true"} or "still scheduled" in g or "is scheduled" in g
    g_no = (
        g in {"no", "false"}
        or "not scheduled" in g
        or "cancelled" in g
        or "canceled" in g
        or "no longer" in g
    )

    p_yes = bool(re.search(r"\b(yes|still scheduled|is scheduled|scheduled)\b", p))
    p_no = bool(re.search(r"\b(no|not scheduled|cancelled|canceled|not anymore|no longer)\b", p))

    if g_yes and p_yes and not p_no:
        return 1
    if g_no and p_no:
        return 1

    # unavailable / missing valid value
    g_unavail = (
        "no currently valid" in g
        or "not available" in g
        or "no valid" in g
        or "is unavailable" in g
    )
    p_unavail = (
        "no information" in p
        or "cannot provide" in p
        or "not available" in p
        or "none" == p
        or p == "not available"
        or "no currently valid" in p
        or "no valid" in p
        or "not provided" in p
        or "unavailable" in p
    )
    if g_unavail and p_unavail:
        return 1

    return 0

def contradiction_heuristic(pred, gold):
    p = normalize_answer(pred)
    g = normalize_answer(gold)

    if not p or not g:
        return 0

    p_yes = bool(re.search(r"\b(yes|still scheduled|is scheduled)\b", p))
    p_no = bool(re.search(r"\b(no|not scheduled|cancelled|canceled|not anymore|no longer)\b", p))

    g_yes = g in {"yes", "true"} or "still scheduled" in g or "is scheduled" in g
    g_no = g in {"no", "false"} or "cancelled" in g or "canceled" in g or "not scheduled" in g or "no longer" in g

    if p_yes and g_no:
        return 1
    if p_no and g_yes:
        return 1

    return 0

def extract_prediction_from_raw(raw, old_pred=""):
    raw = str(raw or "")

    if not raw.strip():
        return str(old_pred or "").strip()

    candidates = []

    for marker in [
        "Final answer:",
        "Final Answer:",
        "Answer briefly:",
        "Answer:",
        "assistant\n",
        "assistant\r\n",
    ]:
        if marker in raw:
            candidates.append(raw.rsplit(marker, 1)[-1])

    candidates.append(raw)

    for cand in candidates:
        cand = cand.strip()
        if not cand:
            continue

        lines = [x.strip() for x in cand.splitlines() if x.strip()]

        # remove leading role labels: assistant / user / system
        while lines and ROLE_RE.match(lines[0]):
            lines.pop(0)

        cleaned = []
        for line in lines:
            if ROLE_RE.match(line):
                if cleaned:
                    break
                continue

            line = ROLE_PREFIX_RE.sub("", line).strip()
            if not line:
                continue

            cleaned.append(line)

        if cleaned:
            ans = " ".join(cleaned).strip()

            # remove obvious prompt echoes if any
            ans = ans.replace("Final answer:", "").strip()
            ans = ans.replace("Final Answer:", "").strip()

            # keep compact answer; if long explanation starts, still keep it for relaxed matching
            return ans

    return str(old_pred or "").strip()

def aggregate_numeric(rows, keys):
    out = {"n": len(rows)}
    for k in keys:
        vals = []
        for r in rows:
            try:
                vals.append(float(r.get(k, 0)))
            except Exception:
                pass
        out[k] = sum(vals) / len(vals) if vals else 0.0
    return out

LLM_NUMERIC_KEYS = [
    "exact_accuracy",
    "relaxed_accuracy",
    "contradiction",
    "evidence_precision",
    "evidence_recall",
    "evidence_f1",
    "exact_evidence_hit",
    "invalid_retrieval_rate",
    "cancelled_retrieval_rate",
    "superseded_retrieval_rate",
    "expired_retrieval_rate",
    "retrieved_count",
    "retrieved_chars",
    "retrieval_sec",
    "gen_sec",
    "prompt_chars",
]

RETR_NUMERIC_KEYS = [
    "evidence_precision",
    "evidence_recall",
    "evidence_f1",
    "exact_evidence_hit",
    "invalid_retrieval_rate",
    "cancelled_retrieval_rate",
    "superseded_retrieval_rate",
    "expired_retrieval_rate",
    "retrieved_count",
    "retrieved_chars",
    "latency_sec",
]

def recompute_llm_metrics(run_dir, rows):
    overall = aggregate_numeric(rows, LLM_NUMERIC_KEYS)

    (run_dir / "metrics_overall.json").write_text(
        json.dumps(overall, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    by_task = defaultdict(list)
    for r in rows:
        by_task[r.get("task_type", "unknown")].append(r)

    task_rows = []
    for task, rs in sorted(by_task.items()):
        agg = aggregate_numeric(rs, LLM_NUMERIC_KEYS)
        agg["task_type"] = task
        task_rows.append(agg)

    write_csv(
        run_dir / "metrics_by_task.csv",
        task_rows,
        ["task_type", "n"] + LLM_NUMERIC_KEYS,
    )

def recompute_retrieval_metrics(run_dir, rows):
    overall = aggregate_numeric(rows, RETR_NUMERIC_KEYS)

    (run_dir / "metrics_overall.json").write_text(
        json.dumps(overall, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    by_task = defaultdict(list)
    for r in rows:
        by_task[r.get("task_type", "unknown")].append(r)

    task_rows = []
    for task, rs in sorted(by_task.items()):
        agg = aggregate_numeric(rs, RETR_NUMERIC_KEYS)
        agg["task_type"] = task
        task_rows.append(agg)

    write_csv(
        run_dir / "metrics_by_task.csv",
        task_rows,
        ["task_type", "n"] + RETR_NUMERIC_KEYS,
    )

def summarize_suite():
    rows = []

    for run_dir in sorted(OUT.iterdir()):
        if not run_dir.is_dir():
            continue

        cfg_path = run_dir / "run_config.json"
        met_path = run_dir / "metrics_overall.json"

        if not cfg_path.exists() or not met_path.exists():
            continue

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        met = json.loads(met_path.read_text(encoding="utf-8"))

        row = dict(cfg)
        for k, v in met.items():
            row[f"metric_{k}"] = v
        rows.append(row)

    fields = [
        "run_id", "block", "run_type",
        "dataset_key", "retriever", "regime",
        "model_key", "ablation_group", "components", "disabled_metadata",
        "top_k", "alpha", "beta", "gamma",
        "metric_n",
        "metric_evidence_f1", "metric_exact_evidence_hit",
        "metric_invalid_retrieval_rate",
        "metric_exact_accuracy", "metric_relaxed_accuracy",
        "metric_contradiction",
        "metric_retrieved_chars",
        "metric_prompt_chars",
        "metric_latency_sec",
        "metric_retrieval_sec",
        "metric_gen_sec",
    ]

    write_csv(STATS / "suite82_summary_fixed.csv", rows, fields)

    write_csv(
        TABLES / "table_main_retrieval_fixed.csv",
        [r for r in rows if r.get("block") == "A_main_retrieval"],
        fields,
    )

    write_csv(
        TABLES / "table_main_llm_timebound_fixed.csv",
        [r for r in rows if r.get("block") == "C_main_llm_timebound"],
        fields,
    )

    write_csv(
        TABLES / "table_external_diagnostics_fixed.csv",
        [r for r in rows if r.get("block") == "D_external_diagnostics"],
        fields,
    )

    return rows

def main():
    changed_runs = 0
    changed_rows = 0

    # backup current summary
    old_summary = STATS / "suite82_summary.csv"
    if old_summary.exists():
        backup = STATS / "suite82_summary_before_parser_fix.csv"
        if not backup.exists():
            shutil.copy2(old_summary, backup)
            print("[BACKUP]", backup)

    for run_dir in sorted(OUT.iterdir()):
        if not run_dir.is_dir():
            continue

        pred_path = run_dir / "predictions.jsonl"
        cfg_path = run_dir / "run_config.json"

        if not pred_path.exists() or not cfg_path.exists():
            continue

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if cfg.get("run_type") != "llm":
            continue

        rows = read_jsonl(pred_path)
        if not rows:
            continue

        backup = run_dir / "predictions.before_parser_fix.jsonl"
        if not backup.exists():
            shutil.copy2(pred_path, backup)

        local_changed = 0

        for r in rows:
            old_pred = str(r.get("prediction", "")).strip()
            raw = r.get("raw_output_tail", "")

            new_pred = extract_prediction_from_raw(raw, old_pred=old_pred)

            # Only replace when old was empty/role label or new is clearly more informative.
            old_norm = normalize_answer(old_pred)
            new_norm = normalize_answer(new_pred)

            should_replace = False
            if old_norm in {"", "assistant", "user", "system"}:
                should_replace = True
            elif len(new_norm) > len(old_norm) + 3 and "final answer" not in new_norm:
                should_replace = True

            if should_replace and new_pred and new_pred != old_pred:
                r["prediction_before_parser_fix"] = old_pred
                r["prediction"] = new_pred
                local_changed += 1

            gold = r.get("gold_answer", "")
            r["exact_accuracy"] = exact_match(r.get("prediction", ""), gold)
            r["relaxed_accuracy"] = relaxed_match(r.get("prediction", ""), gold)
            r["contradiction"] = contradiction_heuristic(r.get("prediction", ""), gold)

        write_jsonl(pred_path, rows)
        recompute_llm_metrics(run_dir, rows)

        if local_changed:
            changed_runs += 1
            changed_rows += local_changed

        print(
            f"[FIXED] {run_dir.name} changed={local_changed} "
            f"relaxed={aggregate_numeric(rows, ['relaxed_accuracy'])['relaxed_accuracy']:.4f}"
        )

    final_rows = summarize_suite()

    print("\n[DONE]")
    print("changed_runs:", changed_runs)
    print("changed_rows:", changed_rows)
    print("fixed summary:", STATS / "suite82_summary_fixed.csv")
    print("fixed main llm:", TABLES / "table_main_llm_timebound_fixed.csv")
    print("fixed external:", TABLES / "table_external_diagnostics_fixed.csv")

if __name__ == "__main__":
    main()
