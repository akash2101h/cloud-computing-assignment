.RECIPEPREFIX = >
PYTHON ?= python
CONFIG ?= training/config.yaml
SUBSET ?=

.PHONY: train
train:
> $(PYTHON) training/train.py --config $(CONFIG) $(if $(SUBSET),--subset $(SUBSET),)
