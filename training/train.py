import argparse
import csv
import json
import os
import platform
import random

import numpy as np
import torch
import transformers
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer, get_linear_schedule_with_warmup


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def build_example(tok, text, raw, max_len):
    prefix = f"Command: {text}\nJSON:"
    full = f"Command: {text}\nJSON: {raw}"
    p_ids = tok(prefix)["input_ids"]
    ids = (tok(full)["input_ids"] + [tok.eos_token_id])[:max_len]
    labels = ([-100] * len(p_ids) + ids[len(p_ids):])[: len(ids)]
    return ids, labels


def collate(batch, pad_id):
    m = max(len(x[0]) for x in batch)
    ids = torch.full((len(batch), m), pad_id, dtype=torch.long)
    lab = torch.full((len(batch), m), -100, dtype=torch.long)
    att = torch.zeros((len(batch), m), dtype=torch.long)
    for i, (a, b) in enumerate(batch):
        ids[i, : len(a)] = torch.tensor(a)
        lab[i, : len(b)] = torch.tensor(b)
        att[i, : len(a)] = 1
    return ids, att, lab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="training/config.yaml")
    ap.add_argument("--subset", type=int, default=0)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))

    set_seed(cfg["seed"])
    torch.set_num_threads(cfg["num_threads"])

    out_dir, loss_csv = cfg["output_dir"], cfg["loss_csv"]
    n_max = cfg["max_examples"]
    if args.subset:
        n_max = min(args.subset, n_max)
        out_dir = "model_artifacts/subset"
        loss_csv = os.path.join(out_dir, "loss.csv")
    os.makedirs(out_dir, exist_ok=True)

    rows = [json.loads(x) for x in open(cfg["train_file"], encoding="utf-8") if x.strip()][:n_max]
    print(f"training on {len(rows)} records, seed {cfg['seed']}", flush=True)

    tok = AutoTokenizer.from_pretrained(cfg["model_name"])
    tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(cfg["model_name"], dtype=torch.float32)
    model.train()

    data = [build_example(tok, r["text"], r["teacher_raw"], cfg["max_length"]) for r in rows]
    bs = cfg["batch_size"]
    steps_per_epoch = (len(data) + bs - 1) // bs
    total = steps_per_epoch * cfg["epochs"]

    opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"])
    sched = get_linear_schedule_with_warmup(opt, int(cfg["warmup_ratio"] * total), total)
    gen = torch.Generator().manual_seed(cfg["seed"])

    losses = []
    for epoch in range(1, cfg["epochs"] + 1):
        perm = torch.randperm(len(data), generator=gen).tolist()
        run = []
        for s in range(0, len(perm), bs):
            batch = [data[i] for i in perm[s : s + bs]]
            ids, att, lab = collate(batch, tok.pad_token_id)
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            run.append(loss.item())
        mean = sum(run) / len(run)
        losses.append(mean)
        print(f"epoch {epoch}/{cfg['epochs']} loss {mean:.4f}", flush=True)

    os.makedirs(os.path.dirname(loss_csv) or ".", exist_ok=True)
    with open(loss_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "loss"])
        for i, v in enumerate(losses, 1):
            w.writerow([i, f"{v:.6f}"])

    model.eval()
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    info = {
        "version": cfg["version"],
        "base_model": cfg["model_name"],
        "records": len(rows),
        "config": cfg,
        "final_loss": losses[-1],
        "python": platform.python_version(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "prompt_format": "Command: {text}\\nJSON:",
    }
    json.dump(info, open(os.path.join(out_dir, "version_info.json"), "w"), indent=2)

    for r in rows[:3]:
        enc = tok(f"Command: {r['text']}\nJSON:", return_tensors="pt")
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=60, do_sample=False, pad_token_id=tok.eos_token_id)
        print(repr(tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)))
    print("saved to", out_dir)


if __name__ == "__main__":
    main()
