import json
import subprocess
import sys

sys.path.insert(0, "worker")
from teacher_client import ask_teacher, load_prompt

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
tmpl = load_prompt()
rows = [json.loads(line) for line in open("data/validation.jsonl", encoding="utf-8")][:N]

with open("/tmp/val_subset.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")

with open("results/prompt_test.jsonl", "w", encoding="utf-8") as out:
    for i, r in enumerate(rows, 1):
        reply = ask_teacher(tmpl, r["text"])
        out.write(json.dumps({"id": r["id"], "prediction": reply}) + "\n")
        print(f"{i}/{N} {r['text']!r}\n   -> {reply!r}", flush=True)

subprocess.run(["python", "tools/score.py", "results/prompt_test.jsonl", "/tmp/val_subset.jsonl"])
