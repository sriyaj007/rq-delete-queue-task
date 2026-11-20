# rq queue deletion: Harbor package

This folder holds a Harbor package for one software-engineering task, for use
with [Harbor](https://github.com/harbor-framework/harbor) and Docker. The task
is a real repository at a fixed commit, a written request, and a hidden
weighted grader that scores a change to that repository. The agent works in one
container; a second container, which the agent never sees, grades the patch it
leaves behind. The table under "Packaged tasks" maps the task folder to its row
in `data/test.parquet`.

The folder contains the reference solution and the hidden grader. A model you
are evaluating must see only the task prompt and its own sandbox, which is what
Harbor gives it. Do not put the other files where that model, or its training
data, can reach them.

## What you need

- Docker with Compose and BuildKit, on Linux, macOS or Windows with WSL.
- Python 3.12 and Harbor 0.26.0: `pip install harbor==0.26.0`.
- Network access while images are built. The task runs offline, except that
  the agent reaches its model's API.
- Each task container is limited to 2 CPUs and 8 GiB.

No GPU, model account or API key is needed for the checks below.

## Quick start

From this folder:

```bash
python verify_bundle.py
harbor run -p tasks/rq_delete_queue_owned_state_contract -a oracle    # the reference fix: reward 1.0
harbor run -p tasks/rq_delete_queue_owned_state_contract -a nop       # no change: reward 0.0
```

1. `verify_bundle.py` checks every file against `checksums.json`.
2. `harbor run` with Harbor's `oracle` agent applies the reference fix and with
   its `nop` agent changes nothing. Harbor builds the agent and verifier images
   on the first run.

## Running an agent

```bash
harbor run -p tasks/rq_delete_queue_owned_state_contract -a <agent> -m <model> --env-file <file with the model API key>
```

The task declares no network for the agent's phase, so agent harnesses are
installed when the image is built: Claude Code and mini-swe-agent. Pass
`--ak skip_install=true` to a harness that would otherwise install itself at
run time. Another harness needs a line in `environment/Dockerfile` that
installs it. `harbor run --help` lists the agents.

## Packaged tasks

| Task folder | `instance_id` in the dataset | Language | Criteria |
| --- | --- | --- | --- |
| `rq_delete_queue_owned_state_contract` | `rq__rq-rq_delete_queue_owned_state_contract` | Python | 9 |

## How a score is produced

- The agent's container holds the repository at its base commit with a fresh
  one-commit history, a local Redis, the test dependencies, and nothing from
  the grading side. The agent runs as an unprivileged user.
- When the agent finishes, a step in the task, running as root, stops every
  process the agent left running and captures its change as a patch against a
  protected copy of the base commit. Only that patch reaches the verifier.
- The verifier is a fresh container with no network. It applies the patch to a
  clean copy of the base commit and runs each criterion as its own program, as
  an unprivileged user, against a fresh Redis.
- The reward is the sum of the weights of the passing criteria, between 0 and
  1. Fence criteria, which describe behaviour the untouched code already has,
  pay only when at least one target criterion passes, so an empty or
  comment-only change scores 0. A failed blocker caps the reward at 0.6. A
  patch that does not apply scores 0.
- An attempt is **invalid**, and gets no reward, when grading itself could not
  be completed: no patch was collected, or Redis could not be started or
  reached. Harbor reports it as an error, not as a score.
- `reward.txt` holds the reward; `report.json` and `ctrf.json` hold every
  criterion's result and output.

## Contents

- `tasks/<task id>/`: one Harbor task: `instruction.md` (the prompt the agent
  receives), `task.toml`, `environment/` (agent image recipe, with the rq
  source archive and the capture step), `tests/` (verifier image recipe,
  `verify.py`, `config.json` with the criteria and weights, and one program per
  criterion under `checks/`) and `solution/` (reference fix).
- `verify_bundle.py`: a standard-library script.
- `evidence/rq/`: records written when the package was made: the author's
  calibration, the verifier reports of Harbor's `oracle` and `nop` runs, the
  agent-image scan, and a summary.
- `manifest.json`, `checksums.json`: versions and file hashes.

## Notes

- Builds download base images and pinned packages. A recipe that builds today
  can stop building when an upstream package is withdrawn.
- The grader executes the submitted code. The isolation described above is a
  boundary, not a security certification.
