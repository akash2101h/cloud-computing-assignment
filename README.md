# Knowledge distillation and deployment of a command-parsing LM

Repository: https://github.com/akash2101h/cloud-computing-assignment

Teacher: phi3.5 (Ollama, temperature 0, seed 42). Student: EleutherAI/pythia-70m, fine-tuned on the first 1,500 cleaned teacher replies (sequence-level distillation), served with FastAPI on a local k3d cluster.

## Requirements
Docker, k3d, kubectl, Python 3.11, make, git, Ollama (with `phi3.5` pulled).

## Build and deploy
    python -m venv .venv && source .venv/bin/activate
    pip install -r service/requirements.txt boto3 pyyaml pytest ruff locust
    make up            # builds images, creates the k3d cluster, secrets, SeaweedFS
    ./scripts/seed.sh  # buckets, commands pool and model files (needs model_artifacts/ locally)
    kubectl apply -f k8s/app.yaml -f k8s/hpa.yaml

Model files are not in Git. They are in the GitHub Releases `v1`, `v2` and `base`, and in the SeaweedFS `models` bucket. To rebuild them locally run `make train` and `make train CONFIG=training/config_v2.yaml`.

## Task 1: teacher labelling
Replace `OLLAMA_HOST_PLACEHOLDER` in `k8s/teacher-jobs.yaml` with the host IP that the cluster can reach, then:

    kubectl apply -f k8s/teacher-jobs.yaml
    python worker/clean.py     # writes datasets/v1/train.jsonl and train.sha256

## Train
    make train SUBSET=50       # quick pipeline check
    make train                 # v1, writes training/loss.csv
    make train CONFIG=training/config_v2.yaml   # v2

## Test
    make test                  # unit tests
    make lint
    python training/eval_model.py --model model_artifacts/v1 --out results/student_v1_raw.jsonl --report results/student_v1.json
    python tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check
    locust -f tools/locustfile.py --headless --users 4 --spawn-rate 4 --run-time 2m --host http://localhost:8080 --csv results/loadtest
    ./scripts/rolling_test.sh ; ./scripts/recovery_test.sh ; ./scripts/coldstart.sh

## Tear down
    make down

## CI
`.github/workflows/ci.yml`: lint, unit tests, model evaluation from the GitHub Release, quality gate (`--min-validity 95`), gitleaks.
- Passing run (v1): https://github.com/akash2101h/cloud-computing-assignment/actions/runs/42449324700
- Failing run at the quality gate (base, untrained Pythia): https://github.com/akash2101h/cloud-computing-assignment/actions/runs/42449897580

## Layout
`cluster/` k3d config, `prompts/` teacher prompt, `worker/` labelling worker and `clean.py`, `training/` config, scripts, loss, `service/` FastAPI app and Dockerfile, `k8s/` manifests, `network/` subnets and NACL, `tests/`, `scripts/`, `results/` evidence, `report/` report.
