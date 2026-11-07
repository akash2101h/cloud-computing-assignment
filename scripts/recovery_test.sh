#!/usr/bin/env bash
cd ~/cloud_assignment && source .venv/bin/activate
locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m \
  --host http://localhost:8080 --csv results/recovery > results/recovery.log 2>&1 &
LP=$!
sleep 30
kubectl -n app get pods | tee results/recovery_pods_before.txt
POD=$(kubectl -n app get pods -o jsonpath='{.items[0].metadata.name}')
echo "deleting $POD"
kubectl -n app delete pod $POD --wait=false
for i in 1 2 3 4 5 6; do sleep 10; kubectl -n app get pods --no-headers | tee -a results/recovery_pods_after.txt; echo ---; done
wait $LP
cp results/loadtest_headers.json results/recovery_headers.json
