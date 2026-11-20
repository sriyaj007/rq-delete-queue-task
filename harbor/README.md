# rq queue deletion: Harbor package

This folder holds a Harbor package for one software-engineering task, for use with [Harbor](https://github.com/harbor-framework/harbor) and Docker. The task is a real repository at a fixed commit, a written request, and a hidden weighted grader that scores a change to that repository. The agent works in one container; a second container, which the agent never sees, grades the patch it leaves behind.

The folder contains the reference solution and the hidden grader. A model you are evaluating must see only the task prompt and its own sandbox, which is what Harbor gives it. Do not put the other files where that model, or its training data, can reach them.

## What you need

- Docker with Compose and BuildKit, on Linux, macOS or Windows with WSL.
- Python 3.12 and Harbor 0.26.0.
- Network access while images are built. The task runs offline; the agent can reach only its model API.

## Run it

```bash
harbor run -p tasks/rq_delete_queue_owned_state_contract -a oracle   # reference solution: 1.0
harbor run -p tasks/rq_delete_queue_owned_state_contract -a nop      # no change: 0.0
```

With a model:

```bash
harbor run -p tasks/rq_delete_queue_owned_state_contract \
  -a <agent> -m <model> --effort <effort> \
  --env-file <file with the model API key>
```

The agent image is offline, so agent harnesses are installed when the image is built (Claude Code and mini-swe-agent). Pass `--ak skip_install=true` to harnesses that would otherwise try to install themselves at run time. Another harness needs a line in `environment/Dockerfile` that installs it.

## Contents

| Path | What it is |
|---|---|
| `tasks/<task>/instruction.md` | The prompt the agent reads |
| `tasks/<task>/task.toml` | Limits: 1,800-second agent limit, 2 CPUs, 8 GB, no network, separate verifier |
| `tasks/<task>/environment/` | The agent image: the repository at the pinned commit with a one-commit history, Redis, the test dependencies, the agent harnesses, and the capture step |
| `tasks/<task>/solution/` | `reference.patch` and `solve.sh` |
| `tasks/<task>/tests/` | The verifier image: `verify.py`, `config.json` (criteria and weights), one program per criterion under `checks/`, `test.sh` |
| `evidence/rq/` | Author calibration, verifier reports for every calibration patch, the agent-image scan, and a summary |
| `manifest.json` | Task metadata |
| `checksums.json` | SHA-256 of every file in this folder |

## How a run is graded

1. When the agent stops, a trusted step in the agent's container (root) stops any processes the agent left running and writes the agent's change as one patch against the baseline commit. Only that patch reaches the verifier.
2. The verifier container, with no network, applies the patch to a clean copy of the pinned commit.
3. Each criterion is its own program, run as an unprivileged user against a fresh Redis. It passes or fails.
4. The reward is the sum of the weights of the passing criteria. Fence criteria, which describe behaviour the untouched code already has, pay only when at least one target criterion passes, so an untouched or comment-only change scores 0. A failed blocker caps the reward at 0.6.
5. `reward.txt` holds the reward; `report.json` and `ctrf.json` hold every criterion's result and output.

## Packaged tasks

| Task folder | Row in `data/test.parquet` | Repository | Language | Criteria |
|---|---|---|---|---|
| `rq_delete_queue_owned_state_contract` | `rq__rq-rq_delete_queue_owned_state_contract` | rq/rq | Python | 9 |
