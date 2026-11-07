#!/usr/bin/env bash
cd ~/cloud_assignment && source .venv/bin/activate
locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 4m \
  --host http://localhost:8080 --csv results/rolling > results/rolling.log 2>&1 &
LP=$!
sleep 20
kubectl -n app set env deploy/parser MODEL_VERSION=v2 MODEL_URI=s3://models/v2
kubectl -n app rollout status deploy/parser
sleep 20
kubectl -n app rollout undo deploy/parser
kubectl -n app rollout status deploy/parser
wait $LP
cp results/loadtest_headers.json results/rolling_headers.json
