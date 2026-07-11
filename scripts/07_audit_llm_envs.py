import json
import subprocess
from pathlib import Path

ROOT = Path("/home/tahiti/TimeBound")
STATS = ROOT / "stats"
STATS.mkdir(parents=True, exist_ok=True)

candidate_pythons = [
    "/home/tahiti/Malashin_Projects/.venv_a100/bin/python",
    "/home/tahiti/IconoBench/.venv_qwen/bin/python",
    "/home/tahiti/ARTeccv/.venv_qwen/bin/python",
    "/home/tahiti/Spec2Test/.venv_qwen/bin/python",
    "/home/tahiti/crypto/.venv_qwen/bin/python",
]

# Also discover any qwen-like envs.
for p in Path("/home/tahiti").glob("*/.venv_qwen/bin/python"):
    candidate_pythons.append(str(p))
for p in Path("/home/tahiti").glob("*/*/.venv_qwen/bin/python"):
    candidate_pythons.append(str(p))

candidate_pythons = sorted(set(candidate_pythons))

probe_code = r'''
import json, sys
info = {"python": sys.executable}
mods = ["torch", "transformers", "accelerate", "safetensors", "bitsandbytes", "flash_attn"]
for m in mods:
    try:
        mod = __import__(m)
        info[m] = getattr(mod, "__version__", "OK")
    except Exception as e:
        info[m] = "MISS: " + str(e)[:160]
try:
    import torch
    info["cuda_available"] = bool(torch.cuda.is_available())
    info["cuda_device_count"] = int(torch.cuda.device_count())
    if torch.cuda.is_available():
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["cuda_version_torch"] = torch.version.cuda
except Exception as e:
    info["cuda_error"] = str(e)
print(json.dumps(info, ensure_ascii=False))
'''

rows = []

for py in candidate_pythons:
    path = Path(py)
    if not path.exists():
        rows.append({
            "python": py,
            "exists": False,
            "ok": False,
            "error": "missing",
        })
        continue

    try:
        res = subprocess.run(
            [py, "-c", probe_code],
            text=True,
            capture_output=True,
            timeout=60,
        )
        if res.returncode == 0:
            obj = json.loads(res.stdout.strip())
            obj["exists"] = True
            obj["ok"] = True
            rows.append(obj)
        else:
            rows.append({
                "python": py,
                "exists": True,
                "ok": False,
                "error": res.stderr[-1000:],
            })
    except Exception as e:
        rows.append({
            "python": py,
            "exists": True,
            "ok": False,
            "error": str(e),
        })

out = STATS / "llm_env_audit.json"
out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps(rows, indent=2, ensure_ascii=False))
print("\nSaved:", out)
