import argparse
import json
import time
from pathlib import Path

def load_tokenizer(model_path):
    from transformers import AutoTokenizer, PreTrainedTokenizerFast

    try:
        return AutoTokenizer.from_pretrained(
            str(model_path),
            trust_remote_code=True,
            local_files_only=True,
            use_fast=True,
        )
    except Exception as e:
        print("[WARN] AutoTokenizer failed:", repr(e))

    tok_json = model_path / "tokenizer.json"
    if not tok_json.exists():
        raise

    print("[FALLBACK] loading tokenizer.json with PreTrainedTokenizerFast")

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--max_new_tokens", type=int, default=64)
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM

    model_path = Path(args.model)
    if not model_path.exists():
        raise SystemExit(f"Missing model path: {model_path}")

    print("=" * 100)
    print("MODEL:", model_path)
    print("CUDA:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
        print("VRAM allocated before:", round(torch.cuda.memory_allocated() / 1024**3, 3), "GB")
    print("=" * 100)

    t0 = time.time()

    tok = load_tokenizer(model_path)

    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        trust_remote_code=True,
        local_files_only=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )

    # silence stale sampling defaults
    model.generation_config.do_sample = False
    model.generation_config.temperature = None
    model.generation_config.top_p = None

    load_sec = time.time() - t0

    prompt = (
        "You are a temporal-memory QA system. "
        "Use only the context. "
        "Context: Alex scheduled a meeting for Monday. Later, Alex cancelled the meeting. "
        "Question: Is the meeting still scheduled? "
        "Answer briefly:"
    )

    if hasattr(tok, "apply_chat_template") and tok.chat_template:
        messages = [{"role": "user", "content": prompt}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    else:
        text = prompt

    inputs = tok(text, return_tensors="pt")
    inputs.pop("token_type_ids", None)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    t1 = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            pad_token_id=tok.pad_token_id or tok.eos_token_id,
        )
    gen_sec = time.time() - t1

    decoded = tok.decode(out[0], skip_special_tokens=True)

    print("\n=== OUTPUT TAIL ===")
    print(decoded[-1200:])

    result = {
        "model": str(model_path),
        "load_sec": round(load_sec, 3),
        "gen_sec": round(gen_sec, 3),
        "max_new_tokens": args.max_new_tokens,
        "cuda": bool(torch.cuda.is_available()),
    }

    if torch.cuda.is_available():
        result["gpu"] = torch.cuda.get_device_name(0)
        result["vram_allocated_gb"] = round(torch.cuda.memory_allocated() / 1024**3, 3)
        result["vram_reserved_gb"] = round(torch.cuda.memory_reserved() / 1024**3, 3)

    print("\n=== RESULT_JSON ===")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
