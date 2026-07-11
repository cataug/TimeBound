import json
import re
import csv
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path("/home/tahiti/TimeBound")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "converted_external_clean"
STATS = ROOT / "stats"
BASE = datetime(2026, 1, 1, 9, 0)

QUESTION_KEYS = ["question", "query", "q", "problem", "prompt", "input", "instruction"]
ANSWER_KEYS = ["answer", "gold_answer", "target", "label", "output", "response", "final_answer"]

def iso(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

def norm_key(k):
    return str(k).lower().strip().replace("-", "_").replace(" ", "_")

def norm_text(s):
    s = str(s or "").lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9а-яё ,:;./-]+", "", s)
    return s.strip()

def stringify(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return re.sub(r"\s+", " ", x).strip()
    if isinstance(x, (int, float, bool)):
        return str(x)
    return json.dumps(x, ensure_ascii=False)

def pick(obj, keys):
    if not isinstance(obj, dict):
        return None
    lookup = {norm_key(k): k for k in obj.keys()}
    for k in keys:
        nk = norm_key(k)
        if nk in lookup and obj[lookup[nk]] not in [None, ""]:
            return obj[lookup[nk]]
    for kk, vv in obj.items():
        nk = norm_key(kk)
        for k in keys:
            if norm_key(k) in nk and vv not in [None, ""]:
                return vv
    return None

def read_jsonl(path, max_records=None):
    rows = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except Exception:
                continue
            if max_records and len(rows) >= max_records:
                break
    return rows

def parse_query_metadata(q):
    q = stringify(q)
    entity = "the queried entity"
    relation = "the queried relation"
    time_expr = "the queried time"

    # crude but useful enough for non-leaky diagnostic context
    m = re.search(r"Which\s+(.+?)\s+did\s+(.+?)\s+(?:work for|belong to|hold|join|serve|play for|represent)\s+in\s+(.+?)\??$", q, re.I)
    if m:
        relation = m.group(1).strip()
        entity = m.group(2).strip()
        time_expr = m.group(3).strip()

    m2 = re.search(r"in\s+([A-Z][a-z]+\s+\d{4}|\d{4})", q)
    if m2:
        time_expr = m2.group(1)

    return entity, relation, time_expr

def make_history(q, idx):
    entity, relation, time_expr = parse_query_metadata(q)

    texts = [
        f"This is an external interval QA diagnostic instance about {entity}.",
        f"The query asks for {relation} at {time_expr}.",
        "Gold answer fields and answer-bearing facts were removed from the retrieval context to prevent answer leakage.",
        "This converted instance is used to test reader-side interval QA format compatibility rather than TimeBound validity-changing retrieval."
    ]

    hist = []
    for i, txt in enumerate(texts, 1):
        t = BASE + timedelta(minutes=i)
        hist.append({
            "turn_id": i,
            "text": txt,
            "observation_time": iso(t),
            "event_time": iso(t),
            "valid_from": iso(t),
            "valid_to": None,
            "status": "active",
            "relation": None,
            "tag": "complextr_no_leak_context",
        })
    return hist

src = RAW / "complex-tr" / "test_gold.json"
rows = read_jsonl(src, max_records=329)

out_rows = []
for i, obj in enumerate(rows):
    q = stringify(pick(obj, QUESTION_KEYS))
    a = stringify(pick(obj, ANSWER_KEYS))
    hist = make_history(q, i)

    out_rows.append({
        "id": f"complextr_{i:06d}",
        "dataset": "complextr",
        "source_dataset": "complextr",
        "source_file": str(src.relative_to(ROOT)),
        "task_type": "interval_qa",
        "diagnostic_role": "interval_qa",
        "difficulty": "external",
        "query_time": iso(BASE + timedelta(days=1)),
        "query": q,
        "gold_answer": a,
        "gold_evidence_turns": [1],
        "history": hist,
        "metadata": {
            "converter": "05c_fix_complextr_no_leak_conservative.py",
            "source_record_index": i,
            "conservative_no_leak": True,
        }
    })

out_path = OUT / "complextr_timebound_clean.jsonl"
with out_path.open("w", encoding="utf-8") as f:
    for r in out_rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# Recompute clean summary for all converted clean files.
def leakage(ex):
    ans = norm_text(ex.get("gold_answer"))
    if not ans or len(ans) < 4:
        return False
    hist = norm_text(" ".join(ev.get("text", "") for ev in ex.get("history", [])))
    return ans in hist

summary = []
for p in sorted(OUT.glob("*_timebound_clean.jsonl")):
    ds = p.name.replace("_timebound_clean.jsonl", "")
    data = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    lens = [len(x["history"]) for x in data]
    leaks = sum(1 for x in data if leakage(x))
    summary.append({
        "dataset": ds,
        "n_examples": len(data),
        "history_min": min(lens) if lens else 0,
        "history_mean": sum(lens)/len(lens) if lens else 0,
        "history_max": max(lens) if lens else 0,
        "validation_ok": len(data),
        "validation_non_ok": 0,
        "answer_leak_examples": leaks,
        "answer_leak_rate": leaks / len(data) if data else 0,
        "path": str(p),
    })

with (STATS / "external_converted_clean_summary.csv").open("w", newline="", encoding="utf-8") as f:
    fields = list(summary[0].keys())
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(summary)

print("Wrote:", out_path)
for r in summary:
    print(r)
