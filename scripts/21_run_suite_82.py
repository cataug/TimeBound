import argparse
import csv
import gc
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/tahiti/TimeBound")
DEFAULT_OUT = ROOT / "outputs" / "suite82"
STATS = ROOT / "stats"
TABLES = ROOT / "tables"

STATS.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# Basic IO
# ---------------------------------------------------------------------

def read_csv(path):
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})

def read_jsonl(path, limit=None):
    path = Path(path)
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
            if limit and len(rows) >= limit:
                break
    return rows, bad

def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def load_jsonl_ids(path):
    path = Path(path)
    ids = set()
    if not path.exists():
        return ids
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                obj = json.loads(line)
                ids.add(obj.get("id") or obj.get("example_id"))
            except Exception:
                pass
    return ids

def safe_float(x, default=0.0):
    try:
        if x in [None, ""]:
            return default
        return float(x)
    except Exception:
        return default

def safe_int(x, default=0):
    try:
        if x in [None, ""]:
            return default
        return int(float(x))
    except Exception:
        return default

# ---------------------------------------------------------------------
# Text normalization and metrics
# ---------------------------------------------------------------------

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

    # common yes/no relaxed cases
    yes_words = {"yes", "still scheduled", "scheduled"}
    no_words = {"no", "not scheduled", "cancelled", "canceled", "not anymore"}

    if g in {"yes", "true"} and any(w in p for w in yes_words):
        return 1
    if g in {"no", "false"} and any(w in p for w in no_words):
        return 1

    return 0

def contradiction_heuristic(pred, gold):
    p = normalize_answer(pred)
    g = normalize_answer(gold)
    if not p or not g:
        return 0

    p_yes = bool(re.search(r"\b(yes|still scheduled|is scheduled)\b", p))
    p_no = bool(re.search(r"\b(no|not scheduled|cancelled|canceled|not anymore)\b", p))
    g_yes = g in {"yes", "true"} or "still scheduled" in g
    g_no = g in {"no", "false"} or "cancelled" in g or "not scheduled" in g

    if p_yes and g_no:
        return 1
    if p_no and g_yes:
        return 1
    return 0

# ---------------------------------------------------------------------
# Temporal parsing
# ---------------------------------------------------------------------

TIME_FORMATS = [
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
]

def parse_time(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def timestamp(s):
    dt = parse_time(s)
    if not dt:
        return None
    return dt.timestamp()

# ---------------------------------------------------------------------
# Retrieval scoring
# ---------------------------------------------------------------------

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_]+")

def tokenize(s):
    return [t.lower() for t in TOKEN_RE.findall(str(s or ""))]

def lexical_similarity(query, docs):
    q_tokens = tokenize(query)
    doc_tokens = [tokenize(d) for d in docs]

    if not docs:
        return []

    df = Counter()
    for toks in doc_tokens:
        for t in set(toks):
            df[t] += 1

    n_docs = max(1, len(docs))

    def idf(t):
        return math.log((1 + n_docs) / (1 + df.get(t, 0))) + 1.0

    def vec(toks):
        c = Counter(toks)
        return {t: c[t] * idf(t) for t in c}

    qv = vec(q_tokens)
    qnorm = math.sqrt(sum(v * v for v in qv.values())) or 1.0

    scores = []
    for toks in doc_tokens:
        dv = vec(toks)
        dnorm = math.sqrt(sum(v * v for v in dv.values())) or 1.0
        dot = 0.0
        for t, v in qv.items():
            dot += v * dv.get(t, 0.0)
        scores.append(dot / (qnorm * dnorm))
    return scores

def event_text(ev, include_metadata=False):
    if not include_metadata:
        return str(ev.get("text", ""))
    parts = [
        ev.get("text", ""),
        f"observation_time {ev.get('observation_time', '')}",
        f"event_time {ev.get('event_time', '')}",
        f"valid_from {ev.get('valid_from', '')}",
        f"valid_to {ev.get('valid_to', '')}",
        f"status {ev.get('status', '')}",
        f"relation {ev.get('relation', '')}",
    ]
    return " ".join(map(str, parts))

def recency_scores(history, query_time=None, disabled=None):
    disabled = disabled or set()
    if "observation_time" in disabled:
        return [0.5 for _ in history]

    times = []
    for ev in history:
        ts = timestamp(ev.get("observation_time"))
        times.append(ts)

    valid_times = [t for t in times if t is not None]
    if not valid_times:
        return [0.5 for _ in history]

    mn, mx = min(valid_times), max(valid_times)
    span = max(mx - mn, 1.0)

    out = []
    for t in times:
        if t is None:
            out.append(0.0)
        else:
            out.append((t - mn) / span)
    return out

def temporal_validity_score(ev, query_time, disabled=None):
    disabled = disabled or set()
    if "query_time" in disabled or "valid_interval" in disabled:
        return 0.5

    qt = parse_time(query_time)
    if not qt:
        return 0.5

    vf = parse_time(ev.get("valid_from"))
    vt = parse_time(ev.get("valid_to"))

    if vf and qt < vf:
        return 0.0
    if vt and qt > vt:
        return 0.0
    if vf or vt:
        return 1.0

    # fallback through event_time if validity interval absent
    if "event_time" not in disabled:
        et = parse_time(ev.get("event_time"))
        if et:
            days = abs((qt - et).total_seconds()) / 86400.0
            return 1.0 / (1.0 + days / 7.0)

    return 0.5

def status_score(ev, disabled=None):
    disabled = disabled or set()
    if "status" in disabled:
        return 0.5

    st = str(ev.get("status", "")).lower()
    if st in ["active", "scheduled", "delayed"]:
        return 1.0
    if st in ["expired"]:
        return 0.20
    if st in ["superseded"]:
        return 0.10
    if st in ["cancelled", "canceled"]:
        return 0.0
    if not st:
        return 0.5
    return 0.5

def relation_boost(ev, disabled=None):
    disabled = disabled or set()
    if "relation_links" in disabled:
        return 0.0
    rel = ev.get("relation")
    if rel:
        return 0.05
    return 0.0

def components_from_string(s):
    if not s:
        return {"semantic", "temporal", "status"}
    return set(x.strip() for x in s.split("+") if x.strip())

def disabled_from_string(s):
    if not s:
        return set()
    return set(x.strip() for x in s.split("+") if x.strip())

def select_turns(ex, retriever, top_k=3, alpha=0.60, beta=0.30, gamma=0.30,
                 components=None, disabled_metadata=None):
    history = ex.get("history", [])
    query = ex.get("query", "")
    query_time = ex.get("query_time", "")

    if not history:
        return []

    if retriever in ["oracle", "oracle_evidence"]:
        gold = set(ex.get("gold_evidence_turns", []))
        return [ev for ev in history if ev.get("turn_id") in gold]

    top_k = max(1, int(top_k or 3))

    if retriever in ["full_history"]:
        return list(history)

    docs = [event_text(ev, include_metadata=False) for ev in history]
    semantic = lexical_similarity(query, docs)
    rec = recency_scores(history, query_time=query_time, disabled=disabled_metadata)
    temporal = [temporal_validity_score(ev, query_time, disabled=disabled_metadata) for ev in history]
    status = [status_score(ev, disabled=disabled_metadata) for ev in history]
    rel = [relation_boost(ev, disabled=disabled_metadata) for ev in history]

    scores = []

    if retriever == "semantic":
        scores = semantic
    elif retriever == "recency":
        scores = rec
    elif retriever == "semantic_recency":
        scores = [0.70 * s + 0.30 * r for s, r in zip(semantic, rec)]
    elif retriever == "chronological":
        # semantic top-N, then choose most recent among them
        n = min(len(history), max(top_k * 4, 10))
        idxs = sorted(range(len(history)), key=lambda i: semantic[i], reverse=True)[:n]
        idxs = sorted(idxs, key=lambda i: rec[i], reverse=True)[:top_k]
        return [history[i] for i in idxs]
    elif retriever in ["timebound", "timebound_ablation"]:
        comps = components or {"semantic", "temporal", "status"}
        for i in range(len(history)):
            pieces = []
            weights = []
            if "semantic" in comps:
                pieces.append(semantic[i])
                weights.append(alpha)
            if "temporal" in comps:
                pieces.append(temporal[i])
                weights.append(beta)
            if "status" in comps:
                pieces.append(status[i])
                weights.append(gamma)

            if not pieces:
                score = 0.0
            else:
                denom = sum(weights) or 1.0
                score = sum(w * p for w, p in zip(weights, pieces)) / denom
            score += rel[i]
            scores.append(score)
    else:
        raise ValueError(f"Unknown retriever: {retriever}")

    idxs = sorted(range(len(history)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [history[i] for i in idxs]

# ---------------------------------------------------------------------
# Evidence metrics
# ---------------------------------------------------------------------

INVALID_STATUSES = {"expired", "superseded", "cancelled", "canceled"}

def evidence_metrics(ex, selected):
    gold = set(ex.get("gold_evidence_turns", []))
    pred = set(ev.get("turn_id") for ev in selected)

    tp = len(gold & pred)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    exact_hit = int(gold == pred) if gold else 0

    invalid = 0
    cancelled = 0
    superseded = 0
    expired = 0

    for ev in selected:
        st = str(ev.get("status", "")).lower()
        if st in INVALID_STATUSES:
            invalid += 1
        if st in ["cancelled", "canceled"]:
            cancelled += 1
        if st == "superseded":
            superseded += 1
        if st == "expired":
            expired += 1

    denom = len(selected) or 1

    return {
        "evidence_precision": precision,
        "evidence_recall": recall,
        "evidence_f1": f1,
        "exact_evidence_hit": exact_hit,
        "retrieved_count": len(selected),
        "gold_evidence_count": len(gold),
        "invalid_retrieval_rate": invalid / denom,
        "cancelled_retrieval_rate": cancelled / denom,
        "superseded_retrieval_rate": superseded / denom,
        "expired_retrieval_rate": expired / denom,
        "retrieved_chars": sum(len(str(ev.get("text", ""))) for ev in selected),
    }

def aggregate_numeric(rows, keys):
    out = {}
    n = len(rows)
    out["n"] = n
    for k in keys:
        vals = []
        for r in rows:
            try:
                vals.append(float(r.get(k, 0)))
            except Exception:
                pass
        out[k] = sum(vals) / len(vals) if vals else 0.0
    return out

def write_retrieval_metrics(run_dir, pred_rows):
    numeric_keys = [
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

    overall = aggregate_numeric(pred_rows, numeric_keys)
    overall_path = run_dir / "metrics_overall.json"
    overall_path.write_text(json.dumps(overall, indent=2, ensure_ascii=False), encoding="utf-8")

    by_task = defaultdict(list)
    for r in pred_rows:
        by_task[r.get("task_type", "unknown")].append(r)

    task_rows = []
    for task, rs in sorted(by_task.items()):
        agg = aggregate_numeric(rs, numeric_keys)
        agg["task_type"] = task
        task_rows.append(agg)

    fields = ["task_type", "n"] + numeric_keys
    write_csv(run_dir / "metrics_by_task.csv", task_rows, fields)

    return overall, task_rows

# ---------------------------------------------------------------------
# Prompting and LLM loading
# ---------------------------------------------------------------------

def load_tokenizer(model_path):
    from transformers import AutoTokenizer, PreTrainedTokenizerFast

    model_path = Path(model_path)

    try:
        return AutoTokenizer.from_pretrained(
            str(model_path),
            trust_remote_code=True,
            local_files_only=True,
            use_fast=True,
        )
    except Exception as e:
        print("[WARN] AutoTokenizer failed:", repr(e), flush=True)

    tok_json = model_path / "tokenizer.json"
    if not tok_json.exists():
        raise RuntimeError(f"Tokenizer fallback failed; no tokenizer.json in {model_path}")

    print("[FALLBACK] loading tokenizer.json with PreTrainedTokenizerFast", flush=True)

    cfg = {}
    for fn in ["tokenizer_config.json", "special_tokens_map.json"]:
        p = model_path / fn
        if p.exists():
            try:
                cfg.update(json.loads(p.read_text(encoding="utf-8", errors="ignore")))
            except Exception:
                pass

    tok = PreTrainedTokenizerFast(tokenizer_file=str(tok_json))

    for attr in ["bos_token", "eos_token", "unk_token", "pad_token"]:
        val = cfg.get(attr)
        if isinstance(val, dict):
            val = val.get("content")
        if isinstance(val, str):
            setattr(tok, attr, val)

    if tok.pad_token is None and tok.eos_token is not None:
        tok.pad_token = tok.eos_token

    if "chat_template" in cfg:
        tok.chat_template = cfg["chat_template"]

    return tok

def load_model_and_tokenizer(model_path):
    import torch
    from transformers import AutoModelForCausalLM

    model_path = Path(model_path)
    tok = load_tokenizer(model_path)

    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        trust_remote_code=True,
        local_files_only=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )

    model.generation_config.do_sample = False
    model.generation_config.temperature = None
    model.generation_config.top_p = None

    return model, tok

def cleanup_model(model=None, tok=None):
    try:
        del model
    except Exception:
        pass
    try:
        del tok
    except Exception:
        pass
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass

def format_memory(ev):
    return (
        f"[T{ev.get('turn_id')}] "
        f"obs={ev.get('observation_time')} | "
        f"event={ev.get('event_time')} | "
        f"valid={ev.get('valid_from')}..{ev.get('valid_to')} | "
        f"status={ev.get('status')} | "
        f"text={ev.get('text')}"
    )

def build_prompt(ex, selected, regime):
    query = ex.get("query", "")

    if regime == "query_only":
        return (
            "You are a temporal reasoning QA system.\n"
            "Answer the question directly and concisely.\n\n"
            f"Question:\n{query}\n\n"
            "Final answer only:"
        )

    if selected:
        context = "\n".join(format_memory(ev) for ev in selected)
    else:
        context = "(empty)"

    return (
        "You are a temporal-memory QA system. Use only the provided context. "
        "Prefer currently valid memories over cancelled, expired, or superseded ones. "
        "If a later update changes an earlier memory, use the later operative fact. "
        "Return only the final answer, without explanation.\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{query}\n\n"
        "Final answer:"
    )

def llm_generate(model, tok, prompt, max_new_tokens=64):
    import torch

    if hasattr(tok, "apply_chat_template") and getattr(tok, "chat_template", None):
        messages = [{"role": "user", "content": prompt}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        text = prompt

    inputs = tok(text, return_tensors="pt")
    inputs.pop("token_type_ids", None)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    t0 = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tok.pad_token_id or tok.eos_token_id,
        )
    gen_sec = time.time() - t0

    decoded = tok.decode(out[0], skip_special_tokens=True)

    # Strip prompt if possible.
    pred = decoded
    if "Final answer:" in pred:
        pred = pred.split("Final answer:")[-1]
    elif "assistant" in pred.lower():
        pred = re.split(r"assistant\s*", pred, flags=re.I)[-1]

    pred = pred.strip()
    pred = pred.split("\n")[0].strip()
    return pred, decoded, gen_sec, len(text)

# ---------------------------------------------------------------------
# Run execution
# ---------------------------------------------------------------------

def run_retrieval(row, out_root, overwrite=False):
    run_id = row["run_id"]
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    pred_path = run_dir / "predictions.jsonl"
    if overwrite and pred_path.exists():
        pred_path.unlink()

    dataset_path = ROOT / row["dataset_path"]
    limit = safe_int(row.get("limit"), 0) or None
    examples, bad = read_jsonl(dataset_path, limit=limit)

    retriever = row.get("retriever") or "timebound"
    top_k = safe_int(row.get("top_k"), 3)
    alpha = safe_float(row.get("alpha"), 0.60)
    beta = safe_float(row.get("beta"), 0.30)
    gamma = safe_float(row.get("gamma"), 0.30)

    components = components_from_string(row.get("components"))
    disabled = disabled_from_string(row.get("disabled_metadata"))

    existing = load_jsonl_ids(pred_path)
    print(f"[RUN] {run_id} retrieval examples={len(examples)} existing={len(existing)}", flush=True)

    for i, ex in enumerate(examples, 1):
        ex_id = ex.get("id", f"ex_{i}")
        if ex_id in existing:
            continue

        t0 = time.time()
        selected = select_turns(
            ex=ex,
            retriever=retriever,
            top_k=top_k,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            components=components,
            disabled_metadata=disabled,
        )
        latency = time.time() - t0
        m = evidence_metrics(ex, selected)

        pred = {
            "id": ex_id,
            "run_id": run_id,
            "block": row.get("block"),
            "run_type": row.get("run_type"),
            "dataset_key": row.get("dataset_key"),
            "task_type": ex.get("task_type", "unknown"),
            "retriever": retriever,
            "top_k": top_k,
            "components": row.get("components"),
            "disabled_metadata": row.get("disabled_metadata"),
            "gold_evidence_turns": ex.get("gold_evidence_turns", []),
            "retrieved_turns": [ev.get("turn_id") for ev in selected],
            "latency_sec": latency,
            **m,
        }
        append_jsonl(pred_path, pred)

        if i % 100 == 0:
            print(f"[{run_id}] {i}/{len(examples)}", flush=True)

    pred_rows, _ = read_jsonl(pred_path)
    overall, task_rows = write_retrieval_metrics(run_dir, pred_rows)

    row_out = dict(row)
    row_out.update({f"metric_{k}": v for k, v in overall.items()})
    (run_dir / "run_config.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] {run_id} retrieval metric_evidence_f1={overall.get('evidence_f1'):.4f}", flush=True)
    return row_out

def regime_to_retriever(regime):
    if regime == "full_history":
        return "full_history"
    if regime == "semantic_rag":
        return "semantic"
    if regime == "recency_rag":
        return "recency"
    if regime == "semantic_recency_rag":
        return "semantic_recency"
    if regime == "timebound_rag":
        return "timebound"
    if regime == "oracle_evidence":
        return "oracle"
    if regime == "query_only":
        return "query_only"
    raise ValueError(f"Unknown LLM regime: {regime}")

def run_llm(row, out_root, overwrite=False):
    run_id = row["run_id"]
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    pred_path = run_dir / "predictions.jsonl"
    if overwrite and pred_path.exists():
        pred_path.unlink()

    dataset_path = ROOT / row["dataset_path"]
    limit = safe_int(row.get("limit"), 0) or None
    examples, bad = read_jsonl(dataset_path, limit=limit)

    model_path = ROOT / row["model_path"]
    if not model_path.exists():
        raise FileNotFoundError(f"Missing model path: {model_path}")

    regime = row.get("regime")
    retriever = regime_to_retriever(regime)
    top_k = safe_int(row.get("top_k"), 3)
    alpha = safe_float(row.get("alpha"), 0.60)
    beta = safe_float(row.get("beta"), 0.30)
    gamma = safe_float(row.get("gamma"), 0.30)
    max_new_tokens = safe_int(row.get("max_new_tokens"), 64)

    existing = load_jsonl_ids(pred_path)
    print(f"[RUN] {run_id} llm examples={len(examples)} existing={len(existing)} model={model_path}", flush=True)

    if len(existing) >= len(examples):
        pred_rows, _ = read_jsonl(pred_path)
        overall, task_rows = write_llm_metrics(run_dir, pred_rows)
        row_out = dict(row)
        row_out.update({f"metric_{k}": v for k, v in overall.items()})
        print(f"[SKIP COMPLETE] {run_id}", flush=True)
        return row_out

    t_load0 = time.time()
    model, tok = load_model_and_tokenizer(model_path)
    load_sec = time.time() - t_load0

    try:
        for i, ex in enumerate(examples, 1):
            ex_id = ex.get("id", f"ex_{i}")
            if ex_id in existing:
                continue

            t0 = time.time()

            if retriever == "query_only":
                selected = []
            else:
                selected = select_turns(
                    ex=ex,
                    retriever=retriever,
                    top_k=top_k,
                    alpha=alpha,
                    beta=beta,
                    gamma=gamma,
                    components={"semantic", "temporal", "status"},
                    disabled_metadata=set(),
                )

            retrieval_sec = time.time() - t0
            prompt = build_prompt(ex, selected, regime=regime)

            pred_text, raw_text, gen_sec, prompt_chars = llm_generate(
                model=model,
                tok=tok,
                prompt=prompt,
                max_new_tokens=max_new_tokens,
            )

            evm = evidence_metrics(ex, selected) if retriever != "query_only" else {
                "evidence_precision": 0.0,
                "evidence_recall": 0.0,
                "evidence_f1": 0.0,
                "exact_evidence_hit": 0,
                "retrieved_count": 0,
                "gold_evidence_count": len(ex.get("gold_evidence_turns", [])),
                "invalid_retrieval_rate": 0.0,
                "cancelled_retrieval_rate": 0.0,
                "superseded_retrieval_rate": 0.0,
                "expired_retrieval_rate": 0.0,
                "retrieved_chars": 0,
            }

            gold = ex.get("gold_answer", "")

            pred = {
                "id": ex_id,
                "run_id": run_id,
                "block": row.get("block"),
                "run_type": row.get("run_type"),
                "dataset_key": row.get("dataset_key"),
                "task_type": ex.get("task_type", "unknown"),
                "model_key": row.get("model_key"),
                "model_path": row.get("model_path"),
                "regime": regime,
                "retriever": retriever,
                "top_k": top_k,
                "query": ex.get("query", ""),
                "gold_answer": gold,
                "prediction": pred_text,
                "exact_accuracy": exact_match(pred_text, gold),
                "relaxed_accuracy": relaxed_match(pred_text, gold),
                "contradiction": contradiction_heuristic(pred_text, gold),
                "gold_evidence_turns": ex.get("gold_evidence_turns", []),
                "retrieved_turns": [ev.get("turn_id") for ev in selected],
                "retrieval_sec": retrieval_sec,
                "gen_sec": gen_sec,
                "load_sec_once": load_sec,
                "prompt_chars": prompt_chars,
                "raw_output_tail": raw_text[-1500:],
                **evm,
            }
            append_jsonl(pred_path, pred)

            if i % 25 == 0:
                print(
                    f"[{run_id}] {i}/{len(examples)} "
                    f"relaxed={pred['relaxed_accuracy']} pred={pred_text[:80]!r}",
                    flush=True,
                )

    finally:
        cleanup_model(model, tok)

    pred_rows, _ = read_jsonl(pred_path)
    overall, task_rows = write_llm_metrics(run_dir, pred_rows)

    row_out = dict(row)
    row_out.update({f"metric_{k}": v for k, v in overall.items()})
    (run_dir / "run_config.json").write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] {run_id} relaxed_acc={overall.get('relaxed_accuracy'):.4f}", flush=True)
    return row_out

def write_llm_metrics(run_dir, pred_rows):
    numeric_keys = [
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

    overall = aggregate_numeric(pred_rows, numeric_keys)
    (run_dir / "metrics_overall.json").write_text(
        json.dumps(overall, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    by_task = defaultdict(list)
    for r in pred_rows:
        by_task[r.get("task_type", "unknown")].append(r)

    task_rows = []
    for task, rs in sorted(by_task.items()):
        agg = aggregate_numeric(rs, numeric_keys)
        agg["task_type"] = task
        task_rows.append(agg)

    fields = ["task_type", "n"] + numeric_keys
    write_csv(run_dir / "metrics_by_task.csv", task_rows, fields)
    return overall, task_rows

# ---------------------------------------------------------------------
# Suite summary
# ---------------------------------------------------------------------

def summarize_suite(out_root):
    out_root = Path(out_root)
    rows = []

    for run_dir in sorted(out_root.iterdir()):
        if not run_dir.is_dir():
            continue

        cfg_path = run_dir / "run_config.json"
        metrics_path = run_dir / "metrics_overall.json"

        if not cfg_path.exists() or not metrics_path.exists():
            continue

        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            met = json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        row = dict(cfg)
        for k, v in met.items():
            row[f"metric_{k}"] = v
        rows.append(row)

    if not rows:
        return []

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

    write_csv(STATS / "suite82_summary.csv", rows, fields)

    # compact LaTeX-ish tables
    main_retrieval = [
        r for r in rows
        if r.get("block") == "A_main_retrieval"
    ]
    if main_retrieval:
        write_csv(
            TABLES / "table_main_retrieval.csv",
            main_retrieval,
            fields,
        )

    main_llm = [
        r for r in rows
        if r.get("block") == "C_main_llm_timebound"
    ]
    if main_llm:
        write_csv(
            TABLES / "table_main_llm_timebound.csv",
            main_llm,
            fields,
        )

    external = [
        r for r in rows
        if r.get("block") == "D_external_diagnostics"
    ]
    if external:
        write_csv(
            TABLES / "table_external_diagnostics.csv",
            external,
            fields,
        )

    return rows

# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def filter_plan(plan, args):
    rows = []
    run_ids = set(args.run_id or [])
    blocks = set(args.block or [])
    run_types = set(args.run_type or [])

    for r in plan:
        if run_ids and r["run_id"] not in run_ids:
            continue
        if blocks and r["block"] not in blocks:
            continue
        if run_types and r["run_type"] not in run_types:
            continue
        rows.append(r)
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=str(ROOT / "stats" / "run_plan_82.csv"))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--run-id", action="append", default=[])
    ap.add_argument("--block", action="append", default=[])
    ap.add_argument("--run-type", action="append", default=[])
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit-runs", type=int, default=0)
    args = ap.parse_args()

    plan = read_csv(args.plan)
    selected = filter_plan(plan, args)

    if args.limit_runs:
        selected = selected[:args.limit_runs]

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    print("=" * 100)
    print("TimeBound Suite82")
    print("plan:", args.plan)
    print("out:", out_root)
    print("selected runs:", len(selected))
    print("=" * 100)

    for r in selected:
        print(r["run_id"], "|", r["block"], "|", r["run_type"], "|", r["dataset_key"], "|", r.get("model_key"), "|", r.get("regime") or r.get("retriever"))

    if args.dry_run:
        return

    summary_rows = []
    for idx, row in enumerate(selected, 1):
        print("\n" + "#" * 100)
        print(f"[SUITE] {idx}/{len(selected)} {row['run_id']}")
        print("#" * 100, flush=True)

        t0 = time.time()
        run_type = row["run_type"]

        try:
            if run_type in ["retrieval", "retrieval_ablation"]:
                out_row = run_retrieval(row, out_root, overwrite=args.overwrite)
            elif run_type == "llm":
                out_row = run_llm(row, out_root, overwrite=args.overwrite)
            else:
                raise ValueError(f"Unknown run_type: {run_type}")

            out_row["suite_status"] = "ok"
            out_row["suite_wall_sec"] = round(time.time() - t0, 3)

        except Exception as e:
            print(f"[ERROR] {row['run_id']}: {type(e).__name__}: {e}", flush=True)
            out_row = dict(row)
            out_row["suite_status"] = "error"
            out_row["suite_error"] = f"{type(e).__name__}: {e}"
            out_row["suite_wall_sec"] = round(time.time() - t0, 3)

            err_path = out_root / row["run_id"] / "ERROR.txt"
            err_path.parent.mkdir(parents=True, exist_ok=True)
            err_path.write_text(out_row["suite_error"], encoding="utf-8")

            cleanup_model(None, None)

        summary_rows.append(out_row)

        # update partial suite summary every run
        summarize_suite(out_root)

    # final status csv
    fields = sorted(set(k for r in summary_rows for k in r.keys()))
    write_csv(STATS / "suite82_run_status.csv", summary_rows, fields)
    final_rows = summarize_suite(out_root)

    print("\n" + "=" * 100)
    print("[DONE] suite selected runs complete")
    print("status:", STATS / "suite82_run_status.csv")
    print("summary:", STATS / "suite82_summary.csv")
    print("outputs:", out_root)
    print("=" * 100)

if __name__ == "__main__":
    main()
