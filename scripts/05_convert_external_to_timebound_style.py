import json
import re
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict

ROOT = Path("/home/tahiti/TimeBound")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "converted_external_selected"
STATS = ROOT / "stats"

OUT.mkdir(parents=True, exist_ok=True)
STATS.mkdir(parents=True, exist_ok=True)

BASE_TIME = datetime(2026, 1, 1, 9, 0)

MAX = {
    "tempreason": 10000,
    "complextr": 329,
    "tcp": 600,
    "locomo": 500,
}

def iso(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

def compact_json(obj, max_chars=2000):
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_chars]

def read_json_or_jsonl(path, max_records=None):
    rows = []

    # First try full JSON for small files.
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb < 512:
        try:
            obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(obj, list):
                rows = obj
            elif isinstance(obj, dict):
                for key in ["data", "examples", "instances", "questions", "train", "validation", "test"]:
                    if isinstance(obj.get(key), list):
                        rows = obj[key]
                        break
                if not rows:
                    rows = [obj]
            else:
                rows = [{"value": obj}]
            if max_records:
                rows = rows[:max_records]
            return rows
        except Exception:
            pass

    # Fallback: JSONL / NDJSON, including .json files that are actually one JSON object per line.
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

def recursive_find_dicts_with_qa(obj, out=None, depth=0):
    if out is None:
        out = []
    if depth > 8:
        return out

    if isinstance(obj, dict):
        q = pick_value(obj, QUESTION_KEYS)
        a = pick_value(obj, ANSWER_KEYS)
        if q is not None and a is not None:
            out.append(obj)
        for v in obj.values():
            recursive_find_dicts_with_qa(v, out, depth + 1)
    elif isinstance(obj, list):
        for x in obj:
            recursive_find_dicts_with_qa(x, out, depth + 1)
    return out

QUESTION_KEYS = [
    "question", "query", "q", "problem", "prompt", "input", "instruction",
]
ANSWER_KEYS = [
    "answer", "gold_answer", "target", "label", "output", "response", "final_answer",
]
CONTEXT_KEYS = [
    "context", "passage", "story", "text", "article", "paragraph", "facts",
    "evidence", "documents", "doc", "premise", "scenario", "schedule",
    "constraints", "conversation", "dialogue", "messages", "sessions",
    "observation", "observations", "memory", "memories",
]

def normalize_key(k):
    return str(k).lower().strip().replace("-", "_").replace(" ", "_")

def pick_value(obj, keys):
    if not isinstance(obj, dict):
        return None

    norm = {normalize_key(k): k for k in obj.keys()}

    # exact / substring priority
    for target in keys:
        t = normalize_key(target)
        if t in norm:
            val = obj[norm[t]]
            if val not in [None, ""]:
                return val

    for k in obj.keys():
        nk = normalize_key(k)
        for target in keys:
            t = normalize_key(target)
            if t in nk and "answer" not in nk.replace(t, ""):
                val = obj[k]
                if val not in [None, ""]:
                    return val

    return None

def stringify_value(x):
    if x is None:
        return ""
    if isinstance(x, str):
        return re.sub(r"\s+", " ", x).strip()
    if isinstance(x, (int, float, bool)):
        return str(x)
    if isinstance(x, list):
        parts = []
        for item in x[:20]:
            s = stringify_value(item)
            if s:
                parts.append(s)
        return " ".join(parts)
    if isinstance(x, dict):
        # Prefer common text fields.
        for k in ["text", "content", "utterance", "message", "sentence", "value"]:
            if k in x:
                s = stringify_value(x[k])
                if s:
                    return s
        return compact_json(x, max_chars=1000)
    return str(x)

def split_to_turns(text, max_turns=40):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return []

    # Prefer sentence-ish chunks.
    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [p.strip() for p in parts if len(p.strip()) > 0]

    if len(parts) <= 1:
        # fallback chunks
        words = text.split()
        chunks = []
        for i in range(0, len(words), 35):
            chunks.append(" ".join(words[i:i+35]))
        parts = chunks

    return parts[:max_turns]

def collect_context_values(obj, depth=0):
    vals = []
    if depth > 7:
        return vals

    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = normalize_key(k)
            if any(t in nk for t in CONTEXT_KEYS):
                vals.append(v)
            else:
                vals.extend(collect_context_values(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj[:50]:
            vals.extend(collect_context_values(item, depth + 1))

    return vals

def build_history_from_object(obj, dataset_name, idx):
    context_vals = collect_context_values(obj)
    texts = []

    for val in context_vals:
        if isinstance(val, list):
            for item in val[:80]:
                s = stringify_value(item)
                if s:
                    texts.append(s)
        else:
            s = stringify_value(val)
            if s:
                texts.append(s)

    if not texts:
        # Use full object except obvious answer fields.
        if isinstance(obj, dict):
            reduced = {}
            for k, v in obj.items():
                nk = normalize_key(k)
                if not any(a in nk for a in ["answer", "label", "target"]):
                    reduced[k] = v
            texts = [compact_json(reduced, max_chars=3000)]
        else:
            texts = [compact_json(obj, max_chars=3000)]

    # Split large text values into memory turns.
    turns_text = []
    for t in texts:
        turns_text.extend(split_to_turns(t, max_turns=20))
        if len(turns_text) >= 60:
            break

    if not turns_text:
        turns_text = [f"External {dataset_name} instance {idx}."]

    hist = []
    for i, txt in enumerate(turns_text[:60], 1):
        t = BASE_TIME + timedelta(minutes=i)
        hist.append({
            "turn_id": i,
            "text": txt,
            "observation_time": iso(t),
            "event_time": iso(t),
            "valid_from": iso(t),
            "valid_to": None,
            "status": "active",
            "relation": None,
            "tag": "external_context",
        })
    return hist

def convert_record(obj, dataset_name, diagnostic_role, source_file, idx):
    q_raw = pick_value(obj, QUESTION_KEYS)
    a_raw = pick_value(obj, ANSWER_KEYS)

    # If no direct QA fields, search nested dicts.
    if q_raw is None or a_raw is None:
        nested = recursive_find_dicts_with_qa(obj)
        if nested:
            obj = nested[0]
            q_raw = pick_value(obj, QUESTION_KEYS)
            a_raw = pick_value(obj, ANSWER_KEYS)

    query = stringify_value(q_raw)
    answer = stringify_value(a_raw)

    if not query:
        query = f"Answer the {diagnostic_role} question for this instance."
    if not answer:
        answer = "UNKNOWN"

    hist = build_history_from_object(obj, dataset_name, idx)

    return {
        "id": f"{dataset_name}_{idx:06d}",
        "dataset": dataset_name,
        "source_dataset": dataset_name,
        "source_file": str(source_file),
        "task_type": diagnostic_role,
        "diagnostic_role": diagnostic_role,
        "difficulty": "external",
        "query_time": iso(BASE_TIME + timedelta(days=1)),
        "query": query,
        "gold_answer": answer,
        "gold_evidence_turns": [1] if hist else [],
        "history": hist,
        "metadata": {
            "converter": "05_convert_external_to_timebound_style.py",
            "source_file": str(source_file),
            "source_record_index": idx,
        }
    }

def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def validate_external(ex):
    errors = []
    if not ex.get("query"):
        errors.append("missing_query")
    if ex.get("gold_answer") in [None, ""]:
        errors.append("missing_gold_answer")
    if not ex.get("history"):
        errors.append("empty_history")
    if not ex.get("gold_evidence_turns"):
        errors.append("missing_gold_evidence")
    turn_ids = {ev.get("turn_id") for ev in ex.get("history", [])}
    for g in ex.get("gold_evidence_turns", []):
        if g not in turn_ids:
            errors.append("gold_evidence_not_in_history")
    return sorted(set(errors)) or ["ok"]

def convert_tempreason():
    files = [
        RAW / "TempReason" / "test_l1.json",
        RAW / "TempReason" / "test_l1_future.json",
        RAW / "TempReason" / "test_l2.json",
        RAW / "TempReason" / "test_l3.json",
    ]

    rows = []
    for fp in files:
        if not fp.exists():
            continue
        remain = MAX["tempreason"] - len(rows)
        if remain <= 0:
            break
        records = read_json_or_jsonl(fp, max_records=remain)
        for obj in records:
            rows.append(convert_record(
                obj=obj,
                dataset_name="tempreason",
                diagnostic_role="temporal_arithmetic",
                source_file=fp.relative_to(ROOT),
                idx=len(rows),
            ))
            if len(rows) >= MAX["tempreason"]:
                break
    return rows

def convert_complextr():
    fp = RAW / "complex-tr" / "test_gold.json"
    rows = []
    if fp.exists():
        records = read_json_or_jsonl(fp, max_records=MAX["complextr"])
        for obj in records:
            rows.append(convert_record(
                obj=obj,
                dataset_name="complextr",
                diagnostic_role="interval_qa",
                source_file=fp.relative_to(ROOT),
                idx=len(rows),
            ))
    return rows

def convert_tcp():
    files = [
        RAW / "TCP" / "TCP_short.jsonl",
        RAW / "TCP" / "TCP_long.jsonl",
    ]
    rows = []
    for fp in files:
        if not fp.exists():
            continue
        records = read_json_or_jsonl(fp, max_records=MAX["tcp"] - len(rows))
        for obj in records:
            rows.append(convert_record(
                obj=obj,
                dataset_name="tcp",
                diagnostic_role="constraint_scheduling",
                source_file=fp.relative_to(ROOT),
                idx=len(rows),
            ))
            if len(rows) >= MAX["tcp"]:
                break
    return rows

def extract_locomo_records():
    fp = RAW / "locomo" / "data" / "locomo10.json"
    if not fp.exists():
        return []

    convs = read_json_or_jsonl(fp)
    records = []

    for conv_idx, conv in enumerate(convs):
        qa_dicts = recursive_find_dicts_with_qa(conv)
        if qa_dicts:
            for qa_idx, qa in enumerate(qa_dicts):
                # Attach conversation as context if not already included.
                merged = {
                    "question": pick_value(qa, QUESTION_KEYS),
                    "answer": pick_value(qa, ANSWER_KEYS),
                    "conversation": conv,
                    "qa": qa,
                    "conversation_index": conv_idx,
                    "qa_index": qa_idx,
                }
                records.append(merged)
                if len(records) >= MAX["locomo"]:
                    return records
        else:
            # fallback one pseudo-question per conversation
            records.append({
                "question": "Retrieve the relevant long-memory information from this conversation.",
                "answer": "See conversation context.",
                "conversation": conv,
                "conversation_index": conv_idx,
            })
            if len(records) >= MAX["locomo"]:
                return records

    return records

def convert_locomo():
    records = extract_locomo_records()
    rows = []
    for obj in records[:MAX["locomo"]]:
        rows.append(convert_record(
            obj=obj,
            dataset_name="locomo",
            diagnostic_role="long_memory_localization",
            source_file=Path("data/raw/locomo/data/locomo10.json"),
            idx=len(rows),
        ))
    return rows

def summarize(name, rows):
    hist_lens = [len(r.get("history", [])) for r in rows]
    ev_lens = [len(r.get("gold_evidence_turns", [])) for r in rows]
    checks = Counter()
    for r in rows:
        for c in validate_external(r):
            checks[c] += 1

    return {
        "dataset": name,
        "n_examples": len(rows),
        "history_min": min(hist_lens) if hist_lens else 0,
        "history_mean": sum(hist_lens) / len(hist_lens) if hist_lens else 0,
        "history_max": max(hist_lens) if hist_lens else 0,
        "gold_evidence_min": min(ev_lens) if ev_lens else 0,
        "gold_evidence_mean": sum(ev_lens) / len(ev_lens) if ev_lens else 0,
        "gold_evidence_max": max(ev_lens) if ev_lens else 0,
        "validation_ok": checks["ok"],
        "validation_non_ok": len(rows) - checks["ok"],
    }, checks

all_outputs = {
    "tempreason": convert_tempreason(),
    "complextr": convert_complextr(),
    "tcp": convert_tcp(),
    "locomo": convert_locomo(),
}

summary_rows = []
validation_rows = []
role_rows = []

for name, rows in all_outputs.items():
    out_path = OUT / f"{name}_timebound.jsonl"
    write_jsonl(out_path, rows)

    summary, checks = summarize(name, rows)
    summary["path"] = str(out_path)
    summary_rows.append(summary)

    role_counter = Counter(r.get("diagnostic_role", "unknown") for r in rows)
    for role, n in role_counter.items():
        role_rows.append({
            "dataset": name,
            "diagnostic_role": role,
            "n": n,
            "share": n / len(rows) if rows else 0,
        })

    for chk, n in checks.items():
        validation_rows.append({
            "dataset": name,
            "check": chk,
            "n_examples": n,
        })

    print(f"[OK] {name}: {len(rows)} -> {out_path}")

# CSV stats
with (STATS / "external_converted_summary.csv").open("w", newline="", encoding="utf-8") as f:
    fields = [
        "dataset", "n_examples", "history_min", "history_mean", "history_max",
        "gold_evidence_min", "gold_evidence_mean", "gold_evidence_max",
        "validation_ok", "validation_non_ok", "path"
    ]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(summary_rows)

with (STATS / "external_converted_roles.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "diagnostic_role", "n", "share"])
    w.writeheader()
    w.writerows(role_rows)

with (STATS / "external_converted_validation.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "check", "n_examples"])
    w.writeheader()
    w.writerows(validation_rows)

# LaTeX snippet
latex = STATS / "latex_external_converted_summary.tex"
with latex.open("w", encoding="utf-8") as f:
    f.write("\\begin{table}[t]\n\\centering\n\\small\n")
    f.write("\\begin{tabular}{llrrr}\n\\toprule\n")
    f.write("Dataset & Diagnostic role & Examples & Avg. turns & Validated \\\\\n")
    f.write("\\midrule\n")
    for row in summary_rows:
        name = row["dataset"]
        role = next((r["diagnostic_role"] for r in role_rows if r["dataset"] == name), "unknown")
        f.write(
            f"{name} & {role.replace('_', ' ')} & "
            f"{row['n_examples']} & {row['history_mean']:.1f} & "
            f"{row['validation_ok']} / {row['n_examples']} \\\\\n"
        )
    f.write("\\bottomrule\n\\end{tabular}\n")
    f.write("\\caption{Converted external diagnostics in TimeBound-style format.}\n")
    f.write("\\label{tab:external_converted_stats}\n")
    f.write("\\end{table}\n")

print("\n=== External converted summary ===")
for r in summary_rows:
    print(r)

print("\nSaved:")
print(STATS / "external_converted_summary.csv")
print(STATS / "external_converted_roles.csv")
print(STATS / "external_converted_validation.csv")
print(STATS / "latex_external_converted_summary.tex")
