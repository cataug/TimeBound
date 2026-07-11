import json
import re
from pathlib import Path
from collections import Counter
import pandas as pd

ROOT = Path("/home/tahiti/TimeBound")
INP = ROOT / "converted_external_selected"
STATS = ROOT / "stats"
STATS.mkdir(parents=True, exist_ok=True)

def norm(s):
    s = str(s or "").lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9а-яё ,:;./-]+", "", s)
    return s.strip()

rows = []

for path in sorted(INP.glob("*_timebound.jsonl")):
    dataset = path.name.replace("_timebound.jsonl", "")
    n = 0
    leaked = 0
    examples = []

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.strip():
                continue
            ex = json.loads(line)
            n += 1

            ans = norm(ex.get("gold_answer", ""))
            hist_text = norm(" ".join(ev.get("text", "") for ev in ex.get("history", [])))

            # Ignore very short answers like yes/no.
            is_leak = bool(ans and len(ans) >= 4 and ans in hist_text)

            if is_leak:
                leaked += 1
                if len(examples) < 5:
                    examples.append({
                        "id": ex.get("id"),
                        "query": ex.get("query"),
                        "answer": ex.get("gold_answer"),
                        "first_turn": ex.get("history", [{}])[0].get("text", "")[:300],
                    })

    rows.append({
        "dataset": dataset,
        "n_examples": n,
        "answer_leak_examples": leaked,
        "answer_leak_rate": leaked / n if n else 0,
        "examples": examples,
    })

df = pd.DataFrame([{k:v for k,v in r.items() if k != "examples"} for r in rows])
df.to_csv(STATS / "external_answer_leakage_summary.csv", index=False)

with (STATS / "external_answer_leakage_examples.json").open("w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2, ensure_ascii=False)

print(df.to_string(index=False))
print("\nSaved:")
print(STATS / "external_answer_leakage_summary.csv")
print(STATS / "external_answer_leakage_examples.json")
