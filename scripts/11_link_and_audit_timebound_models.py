import os
import json
import csv
from pathlib import Path

ROOT = Path("/home/tahiti/TimeBound")
MODELS = ROOT / "models"
STATS = ROOT / "stats"

MODELS.mkdir(parents=True, exist_ok=True)
STATS.mkdir(parents=True, exist_ok=True)

WANTED = {
    "qwen25_coder_1p5b": {
        "canonical": MODELS / "Qwen__Qwen2.5-Coder-1.5B-Instruct",
        "kind": "small coder reader",
        "candidates": [
            Path("/home/tahiti/Spec2Test/models/Qwen__Qwen2.5-Coder-1.5B-Instruct"),
            Path("/home/tahiti/crypto/models/Qwen2.5-Coder-1.5B-Instruct"),
            Path("/home/tahiti/TimeBound/models/Qwen__Qwen2.5-Coder-1.5B-Instruct"),
        ],
        "cache_globs": [
            "/home/tahiti/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots/*",
            "/home/tahiti/crypto/hf_cache/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots/*",
        ],
    },
    "qwen25_coder_7b": {
        "canonical": MODELS / "Qwen__Qwen2.5-Coder-7B-Instruct",
        "kind": "main coder reader",
        "candidates": [
            Path("/home/tahiti/crypto/models/Qwen2.5-Coder-7B-Instruct"),
            Path("/home/tahiti/Spec2Test/models/Qwen__Qwen2.5-Coder-7B-Instruct"),
            Path("/home/tahiti/TimeBound/models/Qwen__Qwen2.5-Coder-7B-Instruct"),
        ],
        "cache_globs": [
            "/home/tahiti/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/*",
            "/home/tahiti/crypto/hf_cache/hub/models--Qwen--Qwen2.5-Coder-7B-Instruct/snapshots/*",
        ],
    },
    "qwen25_7b": {
        "canonical": MODELS / "Qwen__Qwen2.5-7B-Instruct",
        "kind": "general Qwen reader",
        "candidates": [
            Path("/home/tahiti/TimeBound/models/Qwen__Qwen2.5-7B-Instruct"),
            Path("/home/tahiti/Spec2Test/models/Qwen__Qwen2.5-7B-Instruct"),
            Path("/home/tahiti/crypto/models/Qwen2.5-7B-Instruct"),
        ],
        "cache_globs": [
            "/home/tahiti/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/*",
            "/home/tahiti/crypto/hf_cache/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/*",
        ],
    },
    "mistral_7b_v03": {
        "canonical": MODELS / "mistralai__Mistral-7B-Instruct-v0.3",
        "kind": "non-Qwen reader",
        "candidates": [
            Path("/home/tahiti/TimeBound/models/mistralai__Mistral-7B-Instruct-v0.3"),
            Path("/home/tahiti/Spec2Test/models/mistralai__Mistral-7B-Instruct-v0.3"),
            Path("/home/tahiti/crypto/models/Mistral-7B-Instruct-v0.3"),
        ],
        "cache_globs": [
            "/home/tahiti/.cache/huggingface/hub/models--mistralai--Mistral-7B-Instruct-v0.3/snapshots/*",
            "/home/tahiti/crypto/hf_cache/hub/models--mistralai--Mistral-7B-Instruct-v0.3/snapshots/*",
        ],
    },
}

def expand_cache_globs(globs):
    out = []
    for g in globs:
        out.extend(Path("/").glob(g.lstrip("/")))
    return out

def model_ok(path):
    path = Path(path)
    if not path.exists() or not path.is_dir():
        return False, "missing_or_not_dir"

    has_config = (path / "config.json").exists()
    has_tokenizer = any((path / x).exists() for x in [
        "tokenizer.json",
        "tokenizer.model",
        "tokenizer_config.json",
        "vocab.json",
    ])

    weights = (
        list(path.glob("*.safetensors"))
        + list(path.glob("*.bin"))
        + list(path.glob("model-*.safetensors"))
        + list(path.glob("pytorch_model*.bin"))
    )

    if not has_config:
        return False, "no_config"
    if not has_tokenizer:
        return False, "no_tokenizer"
    if not weights:
        return False, "no_weights"

    return True, "ok"

def size_gb(path):
    total = 0
    path = Path(path)
    if not path.exists():
        return 0
    for root, dirs, files in os.walk(path):
        for fn in files:
            fp = Path(root) / fn
            try:
                total += fp.stat().st_size
            except Exception:
                pass
    return total / (1024 ** 3)

def read_config(path):
    cfg_path = Path(path) / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}

rows = []

for key, spec in WANTED.items():
    canonical = spec["canonical"]
    candidates = []
    candidates.extend(spec["candidates"])
    candidates.extend(expand_cache_globs(spec["cache_globs"]))

    # If canonical already exists, prefer it.
    candidates = [canonical] + [p for p in candidates if p != canonical]

    chosen = None
    chosen_reason = "not_found"

    candidate_report = []
    for c in candidates:
        ok, reason = model_ok(c)
        candidate_report.append({
            "path": str(c),
            "exists": c.exists(),
            "ok": ok,
            "reason": reason,
            "size_gb": round(size_gb(c), 2) if c.exists() else 0,
        })
        if ok and chosen is None:
            chosen = c
            chosen_reason = reason

    linked = False
    link_action = "none"

    if chosen is not None:
        # Create canonical symlink only if canonical is absent.
        if canonical.exists():
            link_action = "canonical_exists"
        else:
            try:
                canonical.symlink_to(chosen, target_is_directory=True)
                linked = True
                link_action = f"symlink_created_to:{chosen}"
            except Exception as e:
                link_action = f"symlink_failed:{type(e).__name__}:{e}"

    final_ok, final_reason = model_ok(canonical)
    cfg = read_config(canonical) if final_ok else {}

    row = {
        "key": key,
        "kind": spec["kind"],
        "canonical": str(canonical),
        "available": final_ok,
        "final_reason": final_reason,
        "chosen_source": str(chosen) if chosen else "",
        "link_action": link_action,
        "size_gb": round(size_gb(canonical), 2) if canonical.exists() else 0,
        "model_type": cfg.get("model_type", ""),
        "architectures": "|".join(map(str, cfg.get("architectures", []))) if cfg else "",
        "torch_dtype": cfg.get("torch_dtype", ""),
        "num_hidden_layers": cfg.get("num_hidden_layers", ""),
        "hidden_size": cfg.get("hidden_size", ""),
        "candidate_report": candidate_report,
    }
    rows.append(row)

json_path = STATS / "timebound_model_registry.json"
csv_path = STATS / "timebound_model_registry.csv"
sh_path = STATS / "timebound_model_paths.sh"

json_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

fields = [
    "key", "kind", "available", "canonical", "chosen_source",
    "link_action", "size_gb", "model_type", "architectures",
    "torch_dtype", "num_hidden_layers", "hidden_size", "final_reason",
]

with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})

with sh_path.open("w", encoding="utf-8") as f:
    f.write("# Auto-generated TimeBound model paths\n")
    for r in rows:
        env_name = "TB_MODEL_" + r["key"].upper()
        if r["available"]:
            f.write(f'export {env_name}="{r["canonical"]}"\n')

print("\n=== TimeBound model registry ===")
for r in rows:
    print("=" * 100)
    print("KEY:", r["key"])
    print("KIND:", r["kind"])
    print("AVAILABLE:", r["available"])
    print("PATH:", r["canonical"])
    print("SOURCE:", r["chosen_source"])
    print("ACTION:", r["link_action"])
    print("SIZE_GB:", r["size_gb"])
    print("TYPE:", r["model_type"])
    print("ARCH:", r["architectures"])
    print("REASON:", r["final_reason"])

print("\nSaved:")
print(csv_path)
print(json_path)
print(sh_path)
