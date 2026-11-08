import json
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir, data, out = sys.argv[1], sys.argv[2], sys.argv[3]
tok = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=torch.float32).eval()
with open(data, encoding="utf-8") as f:
    rows = [json.loads(x) for x in f if x.strip()]
with open(out, "w", encoding="utf-8") as o:
    for r in rows:
        enc = tok(f"Command: {r['text']}\nJSON:", return_tensors="pt")
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=60, do_sample=False, pad_token_id=tok.eos_token_id)
        text = tok.decode(gen[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
        o.write(json.dumps({"id": r["id"], "prediction": text.strip().split("\n")[0].strip()}) + "\n")
