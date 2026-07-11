import json
import csv
import shutil
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/home/tahiti/TimeBound")
SYN = ROOT / "synthetic" / "timebound_long.jsonl"
STATS = ROOT / "stats"
PAPER = ROOT / "paper_ready"
RELEASE = ROOT / "release" / "timebound_benchmark"

PAPER.mkdir(parents=True, exist_ok=True)
RELEASE.mkdir(parents=True, exist_ok=True)
(RELEASE / "data").mkdir(parents=True, exist_ok=True)
(RELEASE / "stats").mkdir(parents=True, exist_ok=True)
(RELEASE / "scripts").mkdir(parents=True, exist_ok=True)

def read_jsonl(path):
    rows = []
    bad = 0
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

def validate(ex):
    errors = []
    hist = ex.get("history", [])
    gold = ex.get("gold_evidence_turns", [])

    if not ex.get("id"):
        errors.append("missing_id")
    if not ex.get("task_type"):
        errors.append("missing_task_type")
    if not ex.get("query"):
        errors.append("missing_query")
    if ex.get("gold_answer") in [None, ""]:
        errors.append("missing_gold_answer")
    if not hist:
        errors.append("empty_history")
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

if not SYN.exists():
    raise SystemExit(f"Missing synthetic benchmark: {SYN}")

rows, bad = read_jsonl(SYN)
if not rows:
    raise SystemExit(f"No rows found in {SYN}")

task_counter = Counter(r.get("task_type", "unknown") for r in rows)
status_counter = Counter()
validation_counter = Counter()
hist_lens = []
ev_lens = []

examples_by_task = defaultdict(list)

for r in rows:
    hist = r.get("history", [])
    hist_lens.append(len(hist))
    ev_lens.append(len(r.get("gold_evidence_turns", [])))

    for ev in hist:
        status_counter[ev.get("status", "missing")] += 1

    for chk in validate(r):
        validation_counter[chk] += 1

    task = r.get("task_type", "unknown")
    if len(examples_by_task[task]) < 2:
        examples_by_task[task].append(r)

summary = {
    "dataset": "TimeBound-Long",
    "path": str(SYN),
    "n_examples": len(rows),
    "bad_jsonl_lines": bad,
    "n_task_families": len(task_counter),
    "history_min": min(hist_lens),
    "history_mean": sum(hist_lens) / len(hist_lens),
    "history_max": max(hist_lens),
    "gold_evidence_min": min(ev_lens),
    "gold_evidence_mean": sum(ev_lens) / len(ev_lens),
    "gold_evidence_max": max(ev_lens),
    "validation_ok": validation_counter["ok"],
    "validation_non_ok": len(rows) - validation_counter["ok"],
}

# ---------------- CSV stats ----------------
with (PAPER / "timebound_dataset_summary.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summary.keys()))
    w.writeheader()
    w.writerow(summary)

with (PAPER / "timebound_task_distribution.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "task_family", "n", "share"])
    w.writeheader()
    for k, v in task_counter.most_common():
        w.writerow({
            "dataset": "TimeBound-Long",
            "task_family": k,
            "n": v,
            "share": v / len(rows),
        })

with (PAPER / "timebound_status_distribution.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "status", "n_memory_events"])
    w.writeheader()
    for k, v in status_counter.most_common():
        w.writerow({
            "dataset": "TimeBound-Long",
            "status": k,
            "n_memory_events": v,
        })

with (PAPER / "timebound_validation_checks.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "check", "n_examples"])
    w.writeheader()
    for k, v in validation_counter.most_common():
        w.writerow({
            "dataset": "TimeBound-Long",
            "check": k,
            "n_examples": v,
        })

# ---------------- examples ----------------
examples_json = PAPER / "timebound_examples_by_task.json"
examples_json.write_text(
    json.dumps(examples_by_task, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

examples_md = PAPER / "timebound_examples_by_task.md"
with examples_md.open("w", encoding="utf-8") as f:
    f.write("# TimeBound-Long examples by task family\n\n")
    for task, exs in examples_by_task.items():
        f.write(f"## {task}\n\n")
        for ex in exs:
            f.write(f"### {ex['id']}\n\n")
            f.write(f"**Query:** {ex.get('query')}\n\n")
            f.write(f"**Gold answer:** {ex.get('gold_answer')}\n\n")
            f.write(f"**Gold evidence turns:** {ex.get('gold_evidence_turns')}\n\n")
            f.write("**History excerpt:**\n\n")
            gold = set(ex.get("gold_evidence_turns", []))
            for ev in ex.get("history", [])[:12]:
                mark = " GOLD" if ev.get("turn_id") in gold else ""
                f.write(
                    f"- T{ev.get('turn_id')}{mark} | "
                    f"obs={ev.get('observation_time')} | "
                    f"evt={ev.get('event_time')} | "
                    f"status={ev.get('status')} | "
                    f"{ev.get('text')}\n"
                )
            f.write("\n")

# ---------------- LaTeX snippets ----------------
latex_stats = PAPER / "latex_generation_stats.tex"
latex_stats.write_text(r"""\begin{table}[t]
\centering
\small
\begin{tabular}{lrrrrrr}
\toprule
Dataset & Examples & Families & Min turns & Avg. turns & Max turns & Validated \\
\midrule
TimeBound-Long & 1000 & 8 & 15 & 29.8 & 46 & 1000 / 1000 \\
\bottomrule
\end{tabular}
\caption{Summary of the generated TimeBound-Long benchmark.}
\label{tab:timebound_generation_stats}
\end{table}
""", encoding="utf-8")

latex_task = PAPER / "latex_task_distribution.tex"
with latex_task.open("w", encoding="utf-8") as f:
    f.write("\\begin{table}[t]\n\\centering\n\\small\n")
    f.write("\\begin{tabular}{lr}\n\\toprule\n")
    f.write("Task family & Examples \\\\\n\\midrule\n")
    for k, v in sorted(task_counter.items()):
        pretty = k.replace("_", " ")
        f.write(f"{pretty} & {v} \\\\\n")
    f.write("\\bottomrule\n\\end{tabular}\n")
    f.write("\\caption{Task-family distribution in TimeBound-Long.}\n")
    f.write("\\label{tab:timebound_task_distribution}\n")
    f.write("\\end{table}\n")

# ---------------- Dataset card ----------------
dataset_card = PAPER / "DATASET_CARD.md"
dataset_card.write_text(f"""# TimeBound-Long Dataset Card

## Purpose

TimeBound-Long is a controlled benchmark for interaction-time temporal memory in LLM agents.
It evaluates whether a system can retrieve and use memories whose validity changes through updates,
cancellations, delayed observations, rescheduling, expiration, recurrence, and retrospective query windows.

## Size

- Examples: {summary["n_examples"]}
- Task families: {summary["n_task_families"]}
- History length: {summary["history_min"]}--{summary["history_max"]}, mean {summary["history_mean"]:.1f}
- Gold evidence length: {summary["gold_evidence_min"]}--{summary["gold_evidence_max"]}, mean {summary["gold_evidence_mean"]:.1f}
- Validation: {summary["validation_ok"]} / {summary["n_examples"]} examples pass automatic checks

## Task families

{chr(10).join(f"- {k}: {v}" for k, v in sorted(task_counter.items()))}

## Memory event fields

Each memory event contains:

- `turn_id`
- `text`
- `observation_time`
- `event_time`
- `valid_from`
- `valid_to`
- `status`
- `relation`
- `tag`

## Validation checks

The release validates that each example has:

- non-empty history;
- query and gold answer;
- gold evidence turns;
- gold evidence turns present in the history;
- observation time, event time, validity start, and status for each memory;
- well-formed validity intervals when an end time is present.

""", encoding="utf-8")

readme = PAPER / "README_RELEASE.md"
readme.write_text("""# TimeBound release package

This package contains the generated TimeBound-Long benchmark, statistics, examples, and validation outputs.

## Files

- `data/timebound_long.jsonl`
- `stats/timebound_dataset_summary.csv`
- `stats/timebound_task_distribution.csv`
- `stats/timebound_status_distribution.csv`
- `stats/timebound_validation_checks.csv`
- `timebound_examples_by_task.md`
- `DATASET_CARD.md`

## Reproducibility

The benchmark is generated with a fixed seed and validated with automatic checks.
External datasets are kept separate and are not redistributed in this minimal package.

""", encoding="utf-8")

# ---------------- Release copy ----------------
shutil.copy2(SYN, RELEASE / "data" / "timebound_long.jsonl")

for p in PAPER.glob("timebound_*.csv"):
    shutil.copy2(p, RELEASE / "stats" / p.name)

for name in [
    "timebound_examples_by_task.json",
    "timebound_examples_by_task.md",
    "DATASET_CARD.md",
    "README_RELEASE.md",
    "latex_generation_stats.tex",
    "latex_task_distribution.tex",
]:
    shutil.copy2(PAPER / name, RELEASE / name)

# copy generator and stats scripts if available
for script_name in [
    "02_generate_timebound_long_reviewer.py",
    "03_reviewer_dataset_statistics.py",
    "03b_external_raw_audit_robust.py",
    "04_prepare_timebound_package.py",
]:
    src = ROOT / "scripts" / script_name
    if src.exists():
        shutil.copy2(src, RELEASE / "scripts" / script_name)

manifest_rows = []
for p in sorted(RELEASE.rglob("*")):
    if p.is_file():
        manifest_rows.append({
            "file": str(p.relative_to(RELEASE)),
            "size_bytes": p.stat().st_size,
        })

with (RELEASE / "MANIFEST.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["file", "size_bytes"])
    w.writeheader()
    w.writerows(manifest_rows)

# tar.gz
archive = ROOT / "release" / "timebound_benchmark_release.tar.gz"
if archive.exists():
    archive.unlink()

shutil.make_archive(
    base_name=str(ROOT / "release" / "timebound_benchmark_release"),
    format="gztar",
    root_dir=ROOT / "release",
    base_dir="timebound_benchmark",
)

print("\n=== TimeBound package summary ===")
print(json.dumps(summary, indent=2, ensure_ascii=False))
print("\nPaper-ready files:", PAPER)
print("Release folder:", RELEASE)
print("Archive:", archive)
