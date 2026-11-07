import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from botocore.exceptions import ClientError  # noqa: E402
from s3util import client  # noqa: E402
from teacher_client import ask_teacher, load_prompt  # noqa: E402

SHARD_INDEX = int(os.environ["SHARD_INDEX"])
SHARD_COUNT = int(os.environ["SHARD_COUNT"])
PREFIX = os.environ.get("OUT_PREFIX", "teacher")
LIMIT = int(os.environ.get("LIMIT", "0"))  # 0 = no limit (only for smoke tests)
FLUSH_EVERY = 20

s3 = client()
OUT_KEY = f"{PREFIX}/shard-{SHARD_INDEX}.jsonl"


def my_commands():
    body = s3.get_object(Bucket="datasets", Key="commands_pool.jsonl")["Body"].read().decode("utf-8")
    for line_no, line in enumerate(body.splitlines()):
        if line.strip() and line_no % SHARD_COUNT == SHARD_INDEX:
            yield json.loads(line)


def load_done():
    try:
        body = s3.get_object(Bucket="datasets", Key=OUT_KEY)["Body"].read().decode("utf-8")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return []
        raise
    return [json.loads(x) for x in body.splitlines() if x.strip()]


def flush(records):
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    s3.put_object(Bucket="datasets", Key=OUT_KEY, Body=data.encode("utf-8"))


def teacher_with_retry(tmpl, text):
    for attempt in range(5):
        try:
            return ask_teacher(tmpl, text)
        except Exception as e:  # network or Ollama hiccup
            print(f"retry {attempt + 1}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("teacher unreachable")


def main():
    tmpl = load_prompt(os.environ.get("PROMPT_PATH", "prompts/teacher_prompt.txt"))
    records = load_done()
    done = {r["id"] for r in records}
    print(f"shard {SHARD_INDEX}/{SHARD_COUNT}: resuming with {len(done)} done", flush=True)
    todo = [c for c in my_commands() if c["id"] not in done]
    if LIMIT:
        todo = todo[:LIMIT]
    print(f"{len(todo)} commands to label", flush=True)
    for n, c in enumerate(todo, 1):
        reply = teacher_with_retry(tmpl, c["text"])
        records.append({"id": c["id"], "text": c["text"], "teacher_raw": reply})
        if n % FLUSH_EVERY == 0:
            flush(records)
            print(f"{n}/{len(todo)} uploaded", flush=True)
    flush(records)
    print(f"finished: {len(records)} records in {OUT_KEY}", flush=True)


if __name__ == "__main__":
    main()
