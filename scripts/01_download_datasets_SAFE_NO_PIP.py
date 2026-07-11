from pathlib import Path
import subprocess

ROOT = Path("/home/tahiti/TimeBound")
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

from huggingface_hub import snapshot_download

HF_DATASETS = {
    "TempReason": "tonytan48/TempReason",
    "complex-tr": "tonytan48/complex-tr",
    "TCP": "Beanbagdzf/TCP",
    "multiwoz_v22": "pfb30/multi_woz_v22",
}

for name, repo_id in HF_DATASETS.items():
    out_dir = RAW / name
    print("=" * 100)
    print(f"[HF] {name} <- {repo_id}")
    print("=" * 100)
    snapshot_download(
        repo_id=repo_id,
        repo_type="dataset",
        local_dir=out_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print(f"[OK] saved: {out_dir}")

locomo_dir = RAW / "locomo"
if not locomo_dir.exists():
    print("=" * 100)
    print("[GIT] cloning LoCoMo")
    print("=" * 100)
    subprocess.run(
        ["git", "clone", "--depth", "1", "https://github.com/snap-research/locomo.git", str(locomo_dir)],
        check=True,
    )
else:
    print(f"[SKIP] LoCoMo already exists: {locomo_dir}")

print("\nDone. No packages were installed or upgraded.")
