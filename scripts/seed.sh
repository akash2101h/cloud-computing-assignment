#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
kubectl -n data port-forward svc/seaweedfs 8333:8333 >/dev/null 2>&1 &
PF=$!
trap "kill $PF" EXIT
sleep 4
export S3_ENDPOINT=http://localhost:8333
export AWS_ACCESS_KEY_ID=$(kubectl -n data get secret seaweed-s3 -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
export AWS_SECRET_ACCESS_KEY=$(kubectl -n data get secret seaweed-s3 -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)
python - << 'PY'
import os, sys
sys.path.insert(0, "worker")
from s3util import client
s3 = client()
have = {b["Name"] for b in s3.list_buckets()["Buckets"]}
for b in ("datasets", "models"):
    if b not in have:
        s3.create_bucket(Bucket=b)
s3.upload_file("data/commands_pool.jsonl", "datasets", "commands_pool.jsonl")
for v in ("v1", "v2"):
    d = f"model_artifacts/{v}"
    if os.path.isdir(d):
        for n in os.listdir(d):
            s3.upload_file(f"{d}/{n}", "models", f"{v}/{n}")
print("seeded")
PY
