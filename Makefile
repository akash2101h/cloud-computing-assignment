.RECIPEPREFIX = >
PYTHON ?= python
CONFIG ?= training/config.yaml
SUBSET ?=
CLUSTER ?= cloudlab

.PHONY: train image up down test lint

train:
> $(PYTHON) training/train.py --config $(CONFIG) $(if $(SUBSET),--subset $(SUBSET),)

image:
> docker build -f service/Dockerfile -t parser-service:1 .
> docker build -f worker/Dockerfile -t teacher-worker:1 .

up: image
> k3d cluster create --config cluster/k3d.yaml || k3d cluster start $(CLUSTER)
> kubectl create namespace data --dry-run=client -o yaml | kubectl apply -f -
> kubectl create namespace pipeline --dry-run=client -o yaml | kubectl apply -f -
> kubectl create namespace app --dry-run=client -o yaml | kubectl apply -f -
> ./scripts/up.sh

down:
> k3d cluster delete $(CLUSTER)

test:
> $(PYTHON) -m pytest -q tests

lint:
> ruff check worker service training tests
