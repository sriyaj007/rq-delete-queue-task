---
# Dataset card metadata. Spec: https://github.com/huggingface/hub-docs/blob/main/datasetcard.md?plain=1
pretty_name: rq queue deletion
language:
- en
language_details: en-US
license: other
license_name: mixed-upstream
license_link: LICENSE
license_details: >-
  The task carries code from the rq repository (patch, test_patch,
  grader_files, dockerfile, and the source archive under harbor/), under rq's
  BSD-2-Clause licence. The task text, grader and packaging are copyright 2026
  Sriya Jonnadula.
tags:
- code
- software-engineering
- swe-bench
- agents
- coding-agents
- benchmark
- evaluation
- bug-fixing
- program-repair
- python
annotations_creators:
- expert-generated
language_creators:
- expert-generated
multilinguality:
- monolingual
size_categories:
- n<1K
source_datasets:
- original
task_categories:
- text-generation
task_ids:
- language-modeling
configs:
- config_name: default
  data_files:
  - split: test
    path: data/test.parquet
dataset_info:
  config_name: default
  features:
  - name: instance_id
    dtype: string
  - name: repo
    dtype: string
  - name: base_commit
    dtype: string
  - name: setup_patch
    dtype: string
  - name: problem_statement
    dtype: string
  - name: patch
    dtype: string
  - name: test_patch
    dtype: string
  - name: patch_files
    list: string
  - name: grader
    list:
    - name: criterion
      dtype: string
    - name: weight
      dtype: float64
  - name: grader_files
    list:
    - name: path
      dtype: string
    - name: encoding
      dtype: string
    - name: content
      dtype: string
  - name: dockerfile
    dtype: string
  - name: language
    dtype: string
  - name: repo_license
    dtype: string
  - name: hud_task
    dtype: string
  - name: difficulty
    dtype: string
  - name: agent_runs
    dtype: int64
  - name: agent_rewards
    list: float64
  - name: agent_mean_reward
    dtype: float64
  - name: agent_solve_rate
    dtype: float64
  - name: agent_models
    list: string
  - name: gold_reward
    dtype: float64
  - name: base_reward
    dtype: float64
  splits:
  - name: test
    num_examples: 1
---

# Dataset Card for rq queue deletion

This dataset contains one real software engineering task for evaluating coding
agents, in the format of ExpertCrowd SWE (EC-SWE, arXiv 2611.13246). It is a
missing behaviour in a real open-source repository, pinned to a commit, with a
written problem statement, a reference fix, and a weighted grader backed by
hidden behaviour checks.

## Dataset Details

### Dataset Description

The repository is [rq](https://github.com/rq/rq), a Python library that runs
background jobs from queues kept in Redis, at commit
`399ad6307febe64b20b818f71743b8337d3a1428`. In rq, a queue owns more than its
list of waiting jobs: each queue also has registries of its finished, failed,
canceled, scheduled, deferred and running jobs, and its jobs can sit in places
that all queues share, such as the waiting set of a rate limit or a group.

At that commit, `Queue.delete(delete_jobs=True)` deletes the jobs on the
waiting list and the list itself, and nothing else. A new queue opened under
the old name starts with the old queue's history, results included. Three
separate paths put jobs back on the deleted queue afterwards: the scheduler,
when a scheduled job comes due; the rate limit, when a slot frees; and a job
that was waiting on a job in another queue, when that job finishes. A job in
another queue that depended on a deleted job waits forever.

The problem statement is an incident report from an operator, in the style of
the EC-SWE tickets. It names some of these effects and leaves others to be
found ("Those are only the ones we tripped over."). It delegates one decision
(what happens to a dependent job in another queue, so long as it is not left
waiting) and fixes three things that must not change: a job running at the
moment of deletion keeps its rate-limit slot until it finishes,
`delete_jobs=False` keeps the jobs, and nothing that belongs to another queue
changes, however close its name.

## Uses

### Direct Use

- Evaluating coding agents on a repository-level task: give the agent
  `problem_statement` and a checkout of `repo` at `base_commit`, then score the
  resulting diff with the grader.
- Running the task end to end with Harbor, from the `harbor/` folder (see
  [Running the task](#running-the-task)).
- Studying graders: the row carries the reference fix, the hidden checks, the
  weights and the author's calibration, so the grader can be checked against
  patches of your own.

## Dataset Structure

One split, `test`, with one row. The columns are those of the EC SWE release.

| Field | Type | What it holds |
| --- | --- | --- |
| `instance_id` | string | `<owner>__<repo>-<task>` |
| `repo` | string | upstream GitHub repository, `owner/name` |
| `base_commit` | string | the 40-character upstream commit the task is built on |
| `setup_patch` | string | a patch applied to `base_commit` before the agent starts; empty here |
| `problem_statement` | string | the exact prompt the agent is sent, including a one-line preamble about the workspace (`/workspace/repo`) |
| `patch` | string | the reference fix, non-test files only |
| `test_patch` | string | the test file the reference fix adds |
| `patch_files` | list of string | every file the reference fix touches |
| `grader` | list of (criterion, weight) | the grader's criteria and their weights; weights add up to 1 |
| `grader_files` | list of (path, encoding, content) | the grader as built into the verifier image (`tests/`): one program per criterion, the shared harness, the list of repository tests that pass at `base_commit`, the scoring script and the verifier's Dockerfile. The rq source archive is left out |
| `dockerfile` | string | the environment the agent runs in |
| `language`, `repo_license` | string | from the GitHub API for `repo` |
| `hud_task` | string | the task's folder name under `harbor/tasks/` |
| `difficulty` | string | bucket of `agent_mean_reward`: very hard (under 0.2), hard, medium, easy, very easy (0.8 and up) |
| `agent_runs`, `agent_rewards` | int, list of float | graded agent runs and each run's reward (0 to 1) |
| `agent_mean_reward`, `agent_solve_rate` | float | mean reward, and the share of runs that scored a full 1.0 |
| `agent_models` | list of string | the model those runs used |
| `gold_reward`, `base_reward` | float | reward of the reference fix (1.0) and of the unchanged repository (0.0) |

```python
from datasets import load_dataset

ds = load_dataset("parquet", data_files="data/test.parquet", split="test")
row = ds[0]
print(row["problem_statement"])
```

### At a glance

- **Tasks:** 1
- **Repository:** rq/rq, Python, BSD-2-Clause
- **Criteria:** 9, of which 6 are targets and 3 are fences (2 of them blockers)
- **Reference fix:** `rq/queue.py` (one method rewritten, three helpers added) and a new test file, 228 lines added
- **Model of the graded agent runs:** claude-opus-5-5, effort max, 30-minute agent limit

### Difficulty

Five graded runs of claude-opus-5-5 at effort max, each with a 30-minute agent
limit, graded by the task's verifier.

| Run | Reward | Raw score | Failed criteria |
| --- | --- | --- | --- |
| 1 | 1.00 | 1.00 | none |
| 2 | 0.60 | 0.98 | `repo_suite_green_and_existing_tests_untouched` (blocker) |
| 3 | 1.00 | 1.00 | none |
| 4 | 0.60 | 0.98 | `repo_suite_green_and_existing_tests_untouched` (blocker) |
| 5 | 1.00 | 1.00 | none |
| **Mean** | **0.84** | | |

Solve rate (runs at a full 1.0): 0.6. Difficulty bucket: very easy.

Runs 2 and 4 passed every behaviour check, and both broke the same two
repository tests that pass at `base_commit`,
`tests/test_retry.py::TestRetry::test_retry_interval` and
`tests/test_worker.py::TestWorker::test_handle_retry`, so the blocker cap
applied.

### Tasks

| Instance | Repository | Language | Difficulty | Mean reward |
| --- | --- | --- | --- | --- |
| `rq__rq-rq_delete_queue_owned_state_contract` | rq/rq | Python | very easy | 0.84 |

## The task

### Problem statement

This is the prompt as the agent receives it (`instruction.md`).

```text
Please make your changes directly in /workspace/repo.

Deleting a queue does not get rid of it.

Last Tuesday we retired the legacy-billing queue with `delete(delete_jobs=True)`. It
dropped out of rq info and we moved on. By Thursday it was back. A reminder somebody had
scheduled on it weeks ago came due and the scheduler put it straight back on the queue,
jobs our shared rate limit had been holding back got their turn and landed there as well,
and Priya's exports, on another queue under the same limit, spent the afternoon waiting
for a slot behind jobs of a queue that no longer existed.

Nor did the history go anywhere. We opened a fresh queue under the old name to try the
move and it already had finished, failed and canceled jobs in it, results and all. Over
in invoicing a job that depended on one of the deleted jobs is still waiting on something
that will never run. What happens to jobs like that we leave to you; stuck forever is the
one answer we do not want. Those are only the ones we tripped over.

Deleting a queue with its jobs means all of them, whatever each was doing at the time. One
that is running right then can finish, with the rate limit still counting it until it
does. Asking to keep the jobs keeps them. Nothing that belongs to any other queue changes,
however close its name.

Do not touch the repository's own tests and keep them passing; anything you add belongs
in a file of its own.

Finish with a final response when your changes are ready.
```

### Grader

Each criterion is its own program, run against a fresh Redis as an
unprivileged user in a container the agent never sees. A **target** is
behaviour the unchanged code lacks. A **fence** is behaviour the unchanged code
already has; fences pay only when at least one target passes, so an untouched
or comment-only change scores 0. A failed **blocker** caps the reward at 0.6.
The reward is the sum of the weights of the passing criteria, after the cap.

| # | Criterion | Weight | Kind | What it checks |
| --- | --- | --- | --- | --- |
| 1 | `new_queue_with_the_same_name_starts_empty` | 0.14 | target | A queue opened under the deleted name has nothing waiting and nothing in any registry. |
| 2 | `finished_failed_canceled_jobs_gone_with_results` | 0.15 | target | The deleted queue's finished, failed, canceled and grouped jobs cannot be fetched and have no stored results, and the group lists only the other queue's job. |
| 3 | `jobs_that_had_not_run_yet_are_gone_and_stay_gone` | 0.20 | target | Waiting, scheduled (later and already due) and dependent jobs are gone, and none comes back after a scheduler tick or when the job it waited on finishes. |
| 4 | `rate_limited_jobs_are_gone_and_the_slot_passes_on` | 0.15 | target | Jobs waiting for a rate-limit slot are gone and do not land on the queue when a slot frees, and a slot the deleted queue held lets another queue's job run. |
| 5 | `running_job_keeps_its_rate_limit_slot` | 0.08 | fence | A running rate-limited job keeps its slot until its run ends, then the slot passes on. |
| 6 | `dependent_in_another_queue_is_not_left_waiting` | 0.15 | target | A job in another queue that waited on a deleted job is not left waiting; any other outcome passes. |
| 7 | `delete_jobs_false_keeps_the_jobs` | 0.05 | fence | With `delete_jobs=False` the queue goes but its jobs and results stay readable. |
| 8 | `other_queues_are_untouched` | 0.06 | fence, blocker | Every stored byte of four queues with similar names is unchanged, and shared lists lose only the deleted queue's entries. |
| 9 | `repo_suite_green_and_existing_tests_untouched` | 0.02 | fence, blocker | The repository's test files are unchanged, and every test that passes at `base_commit` (793) still passes. |

Each check uses queue names that do not appear in the problem statement.
Every check except the repository suite gave the same result on three
repeated runs against the unchanged code, gold, alt and careful
(`harbor/evidence/rq/determinism.txt`).

### Calibration

Patches graded with the task's verifier image, exactly as Harbor's separate
verifier runs it. The reports are in `harbor/evidence/rq/`.

| Patch | What it is | Reward |
| --- | --- | --- |
| gold | the reference fix | 1.00 |
| alt | a second correct design: deletes in bulk with direct Redis commands instead of rq's per-job delete, and deletes dependents in other queues instead of canceling them | 1.00 |
| careful | calls rq's per-job delete for every job on the queue's list and in its registries; misses jobs waiting for a rate-limit slot, which sit in a set shared by all queues, and dependents in other queues | 0.70 |
| lazy | also deletes the queue's finished, failed, canceled, deferred and scheduled registry lists, and nothing else | 0.35 |
| noop | a comment only | 0.00 |
| base | no change | 0.00 |
| cheat | wipes keys only for common queue names, and on import writes `reward.txt` and `reward.json` into `/logs/verifier`, `/logs/artifacts` and `/logs` | 0.00 |

| Criterion | gold | alt | careful | lazy | noop | base | cheat |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `new_queue_with_the_same_name_starts_empty` | pass | pass | pass | pass | FAIL | not run | FAIL |
| `finished_failed_canceled_jobs_gone_with_results` | pass | pass | pass | FAIL | FAIL | not run | FAIL |
| `jobs_that_had_not_run_yet_are_gone_and_stay_gone` | pass | pass | pass | FAIL | FAIL | not run | FAIL |
| `rate_limited_jobs_are_gone_and_the_slot_passes_on` | pass | pass | FAIL | FAIL | FAIL | not run | FAIL |
| `running_job_keeps_its_rate_limit_slot` | pass | pass | pass | pass | pass | not run | pass |
| `dependent_in_another_queue_is_not_left_waiting` | pass | pass | FAIL | FAIL | FAIL | not run | FAIL |
| `delete_jobs_false_keeps_the_jobs` | pass | pass | pass | pass | pass | not run | pass |
| `other_queues_are_untouched` | pass | pass | pass | pass | pass | not run | pass |
| `repo_suite_green_and_existing_tests_untouched` | pass | pass | pass | pass | pass | not run | pass |
| **Reward** | **1.00** | **1.00** | **0.70** | **0.35** | **0.00** | **0.00** | **0.00** |

An empty change is scored 0 without running any criterion. The cheat's reward
files never reached the verifier's output folder; its `reward.txt` is 0.0.

## Running the task

The `harbor/` folder makes the task runnable end to end with
[Harbor](https://github.com/harbor-framework/harbor) 0.26.0 and Docker. The
task is packaged as two containers: one for the agent, holding the repository
at its base commit with a one-commit history and nothing from the grading side,
and a separate one that grades the patch the agent leaves behind. Both are
offline; the agent can reach only its model API. The folder holds the task's
complete build context, so both images can be rebuilt from this repository
alone.

```bash
cd harbor
pip install harbor==0.26.0
harbor run -p tasks/rq_delete_queue_owned_state_contract -a oracle   # the reference fix: reward 1.0
harbor run -p tasks/rq_delete_queue_owned_state_contract -a nop      # no change: reward 0.0
harbor run -p tasks/rq_delete_queue_owned_state_contract -a <agent> -m <model>
```

`harbor/README.md` has the requirements and says how a run is graded. The
folder contains the reference fix and the hidden grader, as the row of this
dataset does.

## Dataset Creation

### Curation Rationale

The aim was one task in the EC-SWE format that a current frontier agent does
not solve reliably for reasons that come from the work: finding every place a
queue's jobs can live, including places shared with other queues, while
leaving running jobs, kept jobs and other queues exactly as they were.

### Source Data

#### Data Collection and Processing

The gap was reproduced at the pinned commit with a script before anything else
was written. At that commit it is live upstream. An open pull request,
rq/rq#2584, frees rate-limit slots held by deleted jobs and leaves jobs waiting
for a slot in place; the problem statement asks for the opposite for waiting
jobs, so that change alone fails a check.

The author then wrote the problem statement, the reference fix and one check
per criterion, and graded a ladder of control patches with the verifier image:
no change, a comment only, a shallow fix, a careful but incomplete fix, a
second correct design, and a cheat that special-cases queue names and tries to
write reward files. The agent runs were graded by the same verifier image.

#### Who are the source data producers?

The code comes from the rq project, written by its contributors. The problem
statement, reference fix, checks and grader are by Sriya Jonnadula.

#### Personal and Sensitive Information

The task is about source code. The names in the problem statement are
invented. Upstream code can contain contributor names in comments, licence
headers or metadata, as it does in the upstream repository.

## Recommendations

Report full solves alongside mean reward, and give the model's training cutoff
relative to the base commit's date (2026-11-20).

## Citation

**BibTeX:**

```bibtex
@misc{jonnadula2026rqdelete,
  author       = {Jonnadula, Sriya},
  title        = {{rq queue deletion}},
  year         = {2026},
  howpublished = {\url{https://github.com/sriyaj007/rq-delete-queue-task}}
}
```

## Glossary

- **Gold run:** the task run with the reference fix applied. It must score 1.0.
- **Base run:** the task run on the unchanged repository. It should score low.
- **Reward:** the grader's weighted score for one run, 0 to 1.
- **Target / fence / blocker:** see [Grader](#grader).

## Dataset Card Authors

Sriya Jonnadula
