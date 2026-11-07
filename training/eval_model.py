import argparse
import json
import subprocess

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--report", required=True)
ap.add_argument("--data", default="data/validation.jsonl")
args = ap.parse_args()

torch.set_num_threads(8)
tok = AutoTokenizer.from_pretrained(args.model)
tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.float32).eval()

rows = [json.loads(x) for x in open(args.data, encoding="utf-8") if x.strip()]
with open(args.out, "w", encoding="utf-8") as f:
    for r in rows:
        enc = tok(f"Command: {r['text']}\nJSON:", return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=60, do_sample=False, pad_token_id=tok.eos_token_id)
        text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
        pred = text.strip().split("\n")[0].strip()
        f.write(json.dumps({"id": r["id"], "prediction": pred}) + "\n")

subprocess.run(["python", "tools/score.py", args.out, args.data, "--out", args.report])
print(open(args.report).read())
