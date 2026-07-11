import json
import re
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

ROOT = Path("/home/tahiti/TimeBound")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "converted_external_clean"
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

QUESTION_KEYS = ["question", "query", "q", "problem", "prompt", "input", "instruction"]
ANSWER_KEYS = ["answer", "gold_answer", "target", "label", "output", "response", "final_answer"]
BAD_CONTEXT_KEYS = set([
    "answer", "answers", "gold_answer", "target", "label", "output", "response",
    "final_answer", "qa", "qas", "questions", "question_answer", "question_answers",
])

def iso(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

def norm_key(k):
    return str(k).lower().strip().replace("-", "_").replace(" ", "_")

def norm_text(s):
    s = str(s or "").lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9а-яё ,:;./-]+", "", s)
    return s.strip()

def stringify(x, max_chars=1500):
    if x is None:
        return ""
    if isinstance(x, str):
        return re.sub(r"\s+", " ", x).strip()[:max_chars]
    if isinstance(x, (int, float, bool)):
        return str(x)
    if isinstance(x, list):
        parts = []
        for item in x[:30]:
            s = stringify(item, max_chars=300)
            if s:
                parts.append(s)
        return " ".join(parts)[:max_chars]
    if isinstance(x, dict):
        for key in ["text", "content", "utterance", "message", "sentence", "value"]:
            if key in x:
                return stringify(x[key], max_chars=max_chars)
        cleaned = remove_answer_fields(x)
        return json.dumps(cleaned, ensure_ascii=False)[:max_chars]
    return str(x)[:max_chars]

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
        if any(norm_key(k) == nk or norm_key(k) in nk for k in keys):
            if vv not in [None, ""]:
                return vv
    return None

def read_json_or_jsonl(path, max_records=None):
    rows = []
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
            if max_records:
                rows = rows[:max_records]
            return rows
        except Exception:
            pass

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

def remove_answer_fields(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nk = norm_key(k)
            if nk in BAD_CONTEXT_KEYS:
                continue
            if "answer" in nk or nk in {"target", "label", "output", "response"}:
                continue
            out[k] = remove_answer_fields(v)
        return out
    if isinstance(obj, list):
        return [remove_answer_fields(x) for x in obj[:80]]
    return obj

def split_turns(text, max_turns=60):
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= 1:
        words = text.split()
        parts = [" ".join(words[i:i+35]) for i in range(0, len(words), 35)]
    return parts[:max_turns]

def make_history_from_texts(texts, answer=None, max_turns=60):
    ans_norm = norm_text(answer)
    turns = []

    for t in texts:
        for part in split_turns(t, max_turns=max_turns):
            pnorm = norm_text(part)
            # remove exact answer leak when answer is long enough
            if ans_norm and len(ans_norm) >= 4 and ans_norm in pnorm:
                continue
            if part.strip():
                turns.append(part.strip())
            if len(turns) >= max_turns:
                break
        if len(turns) >= max_turns:
            break

    if not turns:
        turns = ["No external context is provided; answer requires the query itself or task-specific computation."]

    hist = []
    for i, txt in enumerate(turns, 1):
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
            "tag": "external_context_clean",
        })
    return hist

def collect_text_fields(obj, depth=0):
    if depth > 8:
        return []
    vals = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            nk = norm_key(k)
            if nk in BAD_CONTEXT_KEYS or "answer" in nk:
                continue
            if nk in {"text", "context", "passage", "story", "article", "paragraph",
                      "facts", "fact", "evidence", "document", "documents", "doc",
                      "scenario", "schedule", "constraints", "conversation", "dialogue",
                      "messages", "sessions", "memory", "memories", "utterance",
                      "content", "input", "prompt"}:
                s = stringify(v, max_chars=5000)
                if s:
                    vals.append(s)
            else:
                vals.extend(collect_text_fields(v, depth + 1))

    elif isinstance(obj, list):
        for item in obj[:100]:
            vals.extend(collect_text_fields(item, depth + 1))

    return vals

def find_qa_dicts(obj, out=None, depth=0):
    if out is None:
        out = []
    if depth > 8:
        return out
    if isinstance(obj, dict):
        q = pick(obj, QUESTION_KEYS)
        a = pick(obj, ANSWER_KEYS)
        if q is not None and a is not None:
            out.append(obj)
        for v in obj.values():
            find_qa_dicts(v, out, depth + 1)
    elif isinstance(obj, list):
        for x in obj:
            find_qa_dicts(x, out, depth + 1)
    return out

def build_example(dataset, role, source_file, idx, query, answer, context_obj):
    clean_obj = remove_answer_fields(context_obj)
    texts = collect_text_fields(clean_obj)
    if not texts:
        texts = [json.dumps(clean_obj, ensure_ascii=False)[:5000]]

    hist = make_history_from_texts(texts, answer=answer)

    return {
        "id": f"{dataset}_{idx:06d}",
        "dataset": dataset,
        "source_dataset": dataset,
        "source_file": str(source_file),
        "task_type": role,
        "diagnostic_role": role,
        "difficulty": "external",
        "query_time": iso(BASE_TIME + timedelta(days=1)),
        "query": stringify(query, max_chars=1000),
        "gold_answer": stringify(answer, max_chars=1000),
        "gold_evidence_turns": [1] if hist else [],
        "history": hist,
        "metadata": {
            "converter": "05b_convert_external_clean_no_leak.py",
            "source_file": str(source_file),
            "source_record_index": idx,
            "answer_removed_from_context": True,
        }
    }

def convert_tempreason():
    files = [
        RAW / "TempReason" / "test_l1.json",
        RAW / "TempReason" / "test_l1_future.json",
        RAW / "TempReason" / "test_l2.json",
        RAW / "TempReason" / "test_l3.json",
    ]
    out = []

    for fp in files:
        if not fp.exists():
            continue
        records = read_json_or_jsonl(fp, max_records=MAX["tempreason"] - len(out))
        for obj in records:
            q = pick(obj, QUESTION_KEYS)
            a = pick(obj, ANSWER_KEYS)

            # For TempReason, context should not contain answer. Query itself is the problem.
            context_obj = {
                "problem_statement": q or pick(obj, ["input", "prompt"]) or "Temporal arithmetic problem.",
                "note": "This diagnostic tests temporal arithmetic; no answer is provided in memory.",
            }

            out.append(build_example(
                dataset="tempreason",
                role="temporal_arithmetic",
                source_file=fp.relative_to(ROOT),
                idx=len(out),
                query=q or stringify(context_obj["problem_statement"]),
                answer=a,
                context_obj=context_obj,
            ))
            if len(out) >= MAX["tempreason"]:
                return out
    return out

def convert_complextr():
    fp = RAW / "complex-tr" / "test_gold.json"
    out = []
    if not fp.exists():
        return out

    records = read_json_or_jsonl(fp, max_records=MAX["complextr"])
    for obj in records:
        q = pick(obj, QUESTION_KEYS)
        a = pick(obj, ANSWER_KEYS)

        clean_obj = remove_answer_fields(obj)

        # If no context survives, keep question-derived non-answer context.
        texts = collect_text_fields(clean_obj)
        if not texts:
            clean_obj = {
                "temporal_interval_question": q,
                "note": "Gold answer removed from context. External interval QA diagnostic.",
                "source_record_without_answer": remove_answer_fields(obj),
            }

        out.append(build_example(
            dataset="complextr",
            role="interval_qa",
            source_file=fp.relative_to(ROOT),
            idx=len(out),
            query=q,
            answer=a,
            context_obj=clean_obj,
        ))

    return out

def convert_tcp():
    out = []
    files = [
        RAW / "TCP" / "TCP_short.jsonl",
        RAW / "TCP" / "TCP_long.jsonl",
    ]
    for fp in files:
        if not fp.exists():
            continue
        records = read_json_or_jsonl(fp, max_records=MAX["tcp"] - len(out))
        for obj in records:
            q = pick(obj, QUESTION_KEYS)
            a = pick(obj, ANSWER_KEYS)
            out.append(build_example(
                dataset="tcp",
                role="constraint_scheduling",
                source_file=fp.relative_to(ROOT),
                idx=len(out),
                query=q,
                answer=a,
                context_obj=obj,
            ))
            if len(out) >= MAX["tcp"]:
                return out
    return out

def convert_locomo():
    fp = RAW / "locomo" / "data" / "locomo10.json"
    out = []
    if not fp.exists():
        return out

    convs = read_json_or_jsonl(fp)
    for conv_idx, conv in enumerate(convs):
        qas = find_qa_dicts(conv)

        # Remove all QA blocks from context; keep only conversation/dialogue/memory fields.
        context_clean = remove_answer_fields(conv)

        for qa_idx, qa in enumerate(qas):
            q = pick(qa, QUESTION_KEYS)
            a = pick(qa, ANSWER_KEYS)

            out.append(build_example(
                dataset="locomo",
                role="long_memory_localization",
                source_file=fp.relative_to(ROOT),
                idx=len(out),
                query=q,
                answer=a,
                context_obj=context_clean,
            ))

            if len(out) >= MAX["locomo"]:
                return out

    return out

def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def validate(ex):
    errs = []
    if not ex.get("query"):
        errs.append("missing_query")
    if ex.get("gold_answer") in [None, ""]:
        errs.append("missing_gold_answer")
    if not ex.get("history"):
        errs.append("empty_history")
    if not ex.get("gold_evidence_turns"):
        errs.append("missing_gold_evidence")
    turns = {ev.get("turn_id") for ev in ex.get("history", [])}
    for g in ex.get("gold_evidence_turns", []):
        if g not in turns:
            errs.append("gold_evidence_not_in_history")
    return sorted(set(errs)) or ["ok"]

def leakage(ex):
    ans = norm_text(ex.get("gold_answer", ""))
    if not ans or len(ans) < 4:
        return False
    hist = norm_text(" ".join(ev.get("text", "") for ev in ex.get("history", [])))
    return ans in hist

def summarize(name, rows):
    hist_lens = [len(r.get("history", [])) for r in rows]
    ev_lens = [len(r.get("gold_evidence_turns", [])) for r in rows]
    checks = Counter()
    leaks = 0
    for r in rows:
        for c in validate(r):
            checks[c] += 1
        if leakage(r):
            leaks += 1

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
        "answer_leak_examples": leaks,
        "answer_leak_rate": leaks / len(rows) if rows else 0,
    }, checks

datasets = {
    "tempreason": convert_tempreason(),
    "complextr": convert_complextr(),
    "tcp": convert_tcp(),
    "locomo": convert_locomo(),
}

summary_rows = []
role_rows = []
validation_rows = []

for name, rows in datasets.items():
    path = OUT / f"{name}_timebound_clean.jsonl"
    write_jsonl(path, rows)

    summary, checks = summarize(name, rows)
    summary["path"] = str(path)
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

    print(f"[OK] {name}: {len(rows)} -> {path}")

fields = [
    "dataset", "n_examples",
    "history_min", "history_mean", "history_max",
    "gold_evidence_min", "gold_evidence_mean", "gold_evidence_max",
    "validation_ok", "validation_non_ok",
    "answer_leak_examples", "answer_leak_rate", "path",
]

with (STATS / "external_converted_clean_summary.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(summary_rows)

with (STATS / "external_converted_clean_roles.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "diagnostic_role", "n", "share"])
    w.writeheader()
    w.writerows(role_rows)

with (STATS / "external_converted_clean_validation.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["dataset", "check", "n_examples"])
    w.writeheader()
    w.writerows(validation_rows)

latex = STATS / "latex_external_converted_clean_summary.tex"
with latex.open("w", encoding="utf-8") as f:
    f.write("\\begin{table}[t]\n\\centering\n\\small\n")
    f.write("\\begin{tabular}{llrrrr}\n\\toprule\n")
    f.write("Dataset & Diagnostic role & Examples & Avg. turns & Validated & Leak rate \\\\\n")
    f.write("\\midrule\n")
    for row in summary_rows:
        role = next((r["diagnostic_role"] for r in role_rows if r["dataset"] == row["dataset"]), "unknown")
        f.write(
            f"{row['dataset']} & {role.replace('_', ' ')} & "
            f"{row['n_examples']} & {row['history_mean']:.1f} & "
            f"{row['validation_ok']} / {row['n_examples']} & "
            f"{row['answer_leak_rate']:.3f} \\\\\n"
        )
    f.write("\\bottomrule\n\\end{tabular}\n")
    f.write("\\caption{Clean converted external diagnostics in TimeBound-style format. Answer fields are removed from retrieved contexts before evaluation.}\n")
    f.write("\\label{tab:external_converted_clean_stats}\n")
    f.write("\\end{table}\n")

print("\n=== Clean external conversion summary ===")
for r in summary_rows:
    print(r)

print("\nSaved clean conversion to:", OUT)
