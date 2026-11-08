#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

AK=admin
SK=$(kubectl -n data get secret seaweed-s3 -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' 2>/dev/null | base64 -d || true)
[ -z "$SK" ] && SK=$(openssl rand -hex 16)

for ns in data pipeline app; do
  kubectl -n $ns create secret generic seaweed-s3 \
    --from-literal=AWS_ACCESS_KEY_ID="$AK" \
    --from-literal=AWS_SECRET_ACCESS_KEY="$SK" \
    --dry-run=client -o yaml | kubectl apply -f -
done

cat > /tmp/s3.json << JSON
{"identities":[{"name":"admin","credentials":[{"accessKey":"$AK","secretKey":"$SK"}],"actions":["Admin","Read","Write","List","Tagging"]}]}
JSON
kubectl -n data create secret generic seaweed-s3-config --from-file=s3.json=/tmp/s3.json \
  --dry-run=client -o yaml | kubectl apply -f -
rm -f /tmp/s3.json

k3d image import parser-service:1 teacher-worker:1 -c cloudlab
kubectl apply -f k8s/seaweedfs.yaml
kubectl -n data rollout status deploy/seaweedfs --timeout=600s


echo "SeaweedFS is up. Next: scripts/seed.sh, then kubectl apply -f k8s/app.yaml -f k8s/hpa.yaml"
