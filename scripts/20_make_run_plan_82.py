import csv
from pathlib import Path

ROOT = Path("/home/tahiti/TimeBound")
STATS = ROOT / "stats"
STATS.mkdir(parents=True, exist_ok=True)

DATASETS = {
    "timebound_long": "synthetic/timebound_long.jsonl",
    "tempreason": "converted_external_clean/tempreason_timebound_clean.jsonl",
    "complextr": "converted_external_clean/complextr_timebound_clean.jsonl",
    "tcp": "converted_external_clean/tcp_timebound_clean.jsonl",
    "locomo": "converted_external_clean/locomo_timebound_clean.jsonl",
}

MODELS = {
    "qwen25_coder_1p5b": "models/Qwen__Qwen2.5-Coder-1.5B-Instruct",
    "qwen25_coder_7b": "models/Qwen__Qwen2.5-Coder-7B-Instruct",
    "qwen25_7b": "models/Qwen__Qwen2.5-7B-Instruct",
    "mistral_7b_v03": "models/mistralai__Mistral-7B-Instruct-v0.3",
}

rows = []

def add(
    run_id,
    block,
    run_type,
    dataset_key,
    retriever="",
    regime="",
    model_key="",
    ablation_group="",
    components="",
    disabled_metadata="",
    top_k=3,
    alpha=0.60,
    beta=0.30,
    gamma=0.30,
    limit="",
    max_new_tokens=64,
    note="",
):
    rows.append({
        "run_id": run_id,
        "block": block,
        "run_type": run_type,
        "dataset_key": dataset_key,
        "dataset_path": DATASETS[dataset_key],
        "retriever": retriever,
        "regime": regime,
        "model_key": model_key,
        "model_path": MODELS.get(model_key, ""),
        "ablation_group": ablation_group,
        "components": components,
        "disabled_metadata": disabled_metadata,
        "top_k": str(top_k),
        "alpha": str(alpha),
        "beta": str(beta),
        "gamma": str(gamma),
        "limit": str(limit),
        "max_new_tokens": str(max_new_tokens),
        "note": note,
    })

# ---------------------------------------------------------------------
# A. Retrieval-only main on TimeBound-Long: 6 runs
# ---------------------------------------------------------------------
for retr in ["semantic", "recency", "semantic_recency", "chronological", "timebound", "oracle"]:
    add(
        run_id=f"A_tb_retrieval_main_{retr}",
        block="A_main_retrieval",
        run_type="retrieval",
        dataset_key="timebound_long",
        retriever=retr,
        top_k=3,
        note="Main retrieval-only baseline on TimeBound-Long",
    )

# ---------------------------------------------------------------------
# B. Retrieval ablations: 18 runs
# ---------------------------------------------------------------------
score_ablations = {
    "semantic_only": "semantic",
    "temporal_only": "temporal",
    "status_only": "status",
    "semantic_temporal": "semantic+temporal",
    "semantic_status": "semantic+status",
    "temporal_status": "temporal+status",
    "full_timebound": "semantic+temporal+status",
}

for name, comps in score_ablations.items():
    add(
        run_id=f"B_score_{name}",
        block="B_retrieval_ablations",
        run_type="retrieval_ablation",
        dataset_key="timebound_long",
        retriever="timebound_ablation",
        ablation_group="score_components",
        components=comps,
        top_k=3,
        note="TimeBound score-component ablation",
    )

metadata_ablations = [
    "no_status",
    "no_valid_interval",
    "no_event_time",
    "no_observation_time",
    "no_relation_links",
    "no_query_time",
    "full_metadata",
]

for name in metadata_ablations:
    disabled = "" if name == "full_metadata" else name.replace("no_", "")
    add(
        run_id=f"B_metadata_{name}",
        block="B_retrieval_ablations",
        run_type="retrieval_ablation",
        dataset_key="timebound_long",
        retriever="timebound_ablation",
        ablation_group="metadata_removal",
        components="semantic+temporal+status",
        disabled_metadata=disabled,
        top_k=3,
        note="TimeBound metadata-removal ablation",
    )

for k in [1, 3, 5, 7]:
    add(
        run_id=f"B_topk_k{k}",
        block="B_retrieval_ablations",
        run_type="retrieval_ablation",
        dataset_key="timebound_long",
        retriever="timebound",
        ablation_group="topk_sensitivity",
        components="semantic+temporal+status",
        top_k=k,
        note="Top-k sensitivity for TimeBound retrieval",
    )

# ---------------------------------------------------------------------
# C. Main LLM-reader runs on TimeBound-Long: 4 models x 6 regimes = 24
# ---------------------------------------------------------------------
reader_models = [
    "qwen25_coder_1p5b",
    "qwen25_coder_7b",
    "qwen25_7b",
    "mistral_7b_v03",
]

main_regimes = [
    "full_history",
    "semantic_rag",
    "recency_rag",
    "semantic_recency_rag",
    "timebound_rag",
    "oracle_evidence",
]

for model in reader_models:
    for regime in main_regimes:
        add(
            run_id=f"C_llm_timebound_{model}_{regime}",
            block="C_main_llm_timebound",
            run_type="llm",
            dataset_key="timebound_long",
            model_key=model,
            regime=regime,
            top_k=3,
            max_new_tokens=64,
            note="Main local LLM reader run on TimeBound-Long",
        )

# ---------------------------------------------------------------------
# D. External diagnostics: 34 runs
# ---------------------------------------------------------------------
# D1. Retrieval-capable diagnostics: TCP and LoCoMo x 5 retrievers = 10
for ds in ["tcp", "locomo"]:
    for retr in ["semantic", "recency", "semantic_recency", "chronological", "timebound"]:
        add(
            run_id=f"D_external_retrieval_{ds}_{retr}",
            block="D_external_diagnostics",
            run_type="retrieval",
            dataset_key=ds,
            retriever=retr,
            top_k=3,
            note="External retrieval-capable diagnostic",
        )

# D2. Reader-only diagnostics: TempReason and ComplexTR x 4 readers = 8
for ds in ["tempreason", "complextr"]:
    for model in reader_models:
        add(
            run_id=f"D_external_reader_{ds}_{model}_query_only",
            block="D_external_diagnostics",
            run_type="llm",
            dataset_key=ds,
            model_key=model,
            regime="query_only",
            top_k=0,
            max_new_tokens=64,
            note="External reader-only diagnostic",
        )

# D3. TCP and LoCoMo reader diagnostics: 2 datasets x 4 readers x 2 regimes = 16
for ds in ["tcp", "locomo"]:
    for model in reader_models:
        for regime in ["semantic_rag", "timebound_rag"]:
            add(
                run_id=f"D_external_reader_{ds}_{model}_{regime}",
                block="D_external_diagnostics",
                run_type="llm",
                dataset_key=ds,
                model_key=model,
                regime=regime,
                top_k=3,
                max_new_tokens=64,
                note="External reader diagnostic with retrieval context",
            )

assert len(rows) == 82, f"Expected 82 runs, got {len(rows)}"

out = STATS / "run_plan_82.csv"
fields = [
    "run_id", "block", "run_type",
    "dataset_key", "dataset_path",
    "retriever", "regime",
    "model_key", "model_path",
    "ablation_group", "components", "disabled_metadata",
    "top_k", "alpha", "beta", "gamma",
    "limit", "max_new_tokens", "note",
]

with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"[OK] wrote {out}")
print(f"[OK] runs: {len(rows)}")

by_block = {}
for r in rows:
    by_block[r["block"]] = by_block.get(r["block"], 0) + 1

print("\nRuns by block:")
for k, v in by_block.items():
    print(f"  {k}: {v}")

print("\nPlan:")
print("  A main retrieval:", 6)
print("  B retrieval ablations:", 18)
print("  C main LLM TimeBound:", 24)
print("  D external diagnostics:", 34)
print("  TOTAL:", 82)
