import json
from pathlib import Path
import pandas as pd

ROOT = Path("/home/tahiti/TimeBound")
STATS = ROOT / "stats"
STATS.mkdir(parents=True, exist_ok=True)

RAW = ROOT / "data" / "raw"

def count_lines(path):
    n = 0
    bad = 0
    first_obj_type = None

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            n += 1
            if n <= 20:
                try:
                    obj = json.loads(s)
                    if first_obj_type is None:
                        first_obj_type = type(obj).__name__
                except Exception:
                    bad += 1
            elif n % 100000 == 0:
                pass

    return n, bad, first_obj_type or "unknown"

def try_json_container(path, max_mb=512):
    size_mb = path.stat().st_size / (1024 * 1024)

    if size_mb > max_mb:
        n, bad, first_type = count_lines(path)
        return n, f"line_count_large_file:first={first_type}:sample_bad={bad}"

    text = path.read_text(encoding="utf-8", errors="ignore")

    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return len(obj), "json.list"
        if isinstance(obj, dict):
            for k in ["data", "examples", "instances", "questions", "train", "validation", "test"]:
                if isinstance(obj.get(k), list):
                    return len(obj[k]), f"json.dict.{k}"
            return len(obj), "json.dict.keys"
        return None, f"json.{type(obj).__name__}"
    except Exception:
        n, bad, first_type = count_lines(path)
        return n, f"jsonl_or_ndjson:first={first_type}:sample_bad={bad}"

rows = []

for p in sorted(RAW.rglob("*")):
    if not p.is_file():
        continue
    if p.suffix.lower() not in [".json", ".jsonl"]:
        continue

    size_mb = p.stat().st_size / (1024 * 1024)
    n, container = try_json_container(p)

    rows.append({
        "dataset_root": str(p.relative_to(RAW)).split("/")[0],
        "file": str(p.relative_to(ROOT)),
        "size_mb": round(size_mb, 2),
        "n_records_or_lines": n,
        "container": container,
    })

df = pd.DataFrame(rows)
out = STATS / "external_raw_audit_robust.csv"
df.to_csv(out, index=False)

print(df.to_string(index=False))
print("\nSaved:", out)
