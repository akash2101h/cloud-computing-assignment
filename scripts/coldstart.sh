#!/usr/bin/env bash
cd ~/cloud_assignment
: > results/coldstart.txt
for run in 1 2 3; do
  kubectl -n app delete pods --all --wait=true
  kubectl -n app rollout status deploy/parser --timeout=300s
  sleep 5
  kubectl -n app get pods -o json | python3 -c '
import json, sys
from datetime import datetime
d = json.load(sys.stdin)
f = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
for p in d["items"]:
    if p["metadata"].get("deletionTimestamp"):
        continue
    c = f(p["metadata"]["creationTimestamp"])
    r = [x for x in p["status"]["conditions"] if x["type"] == "Ready"][0]
    print("run '"$run"'", p["metadata"]["name"], int((f(r["lastTransitionTime"]) - c).total_seconds()), "s")
' | tee -a results/coldstart.txt
done
for p in $(kubectl -n app get pods -o name); do echo "== $p"; kubectl -n app logs $p | grep -E "downloading|model loaded"; done | tee results/coldstart_logs.txt
python3 - << 'PY'
import re, statistics
v = [int(m.group(1)) for l in open("results/coldstart.txt") for m in [re.search(r"(\d+) s", l)] if m]
print("values:", v, "median:", statistics.median(v))
PY
