# AI use

## Tools
- Claude (Anthropic), as a step-by-step assistant while building the project.
- phi3.5 via Ollama, as the fixed teacher model for labelling (required by the assignment).

## What Claude was used for
- Explaining the task and giving the order of the steps.
- Drafting the teacher prompt, worker, `clean.py`, training and evaluation scripts, the FastAPI service, Dockerfiles, Kubernetes manifests, the NACL rules, subnet table, Makefile, unit tests and the CI workflow.
- Diagnosing errors from pasted logs (for example the WSL network problem, the 502 errors during rollout, and ruff findings).
- Working out the cost, SLO and error-budget numbers, and drafting the review table.

## How the output was checked
- Every script was run and its real output inspected. Nothing was reported without a measured result.
- Teacher prompt: tested on 20 validation commands, then fixed once (stop sequences and extra slot rules). The prompt was therefore tuned while looking at validation examples, so the teacher's validation score may be slightly optimistic. The prompt was locked before the 3,000-command run.
- Data: shard check showed 3000 unique ids with none missing or repeated; `clean.py` was run twice and gave the same SHA-256, and the counts add up.
- Training: `make train SUBSET=50` first, then the full run; the three models were scored with `tools/score.py`.
- Service: tested locally in Docker at 1 CPU and 1 GiB (50 requests, no OOM kill), with `FAULT_INJECT=1`, and then on Kubernetes under Locust load.
- Rolling update: the first attempt had about 2.4% failed requests (502s), which I traced to pods being stopped before the router dropped them. I added a `preStop` sleep and reran, getting 0.18%.
- NACL: checked with `nacl_sim.py` on the sample packets and on 8 extra packets I wrote.
- CI: confirmed that the gate passes for the trained model and fails for the untrained one.
- Security: gitleaks in CI, plus a grep for keys before pushing. No credentials are in the repo.

## Not delegated
Running every command, reading the results, deciding what to report, and writing the report and reflection.
