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
    num_bytes: 101646
    num_examples: 1
  download_size: 64782
  dataset_size: 101646
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
`399ad6307febe64b20b818f71743b8337d3a1428`. Deleting a queue together with its
jobs (`Queue.delete(delete_jobs=True)`) leaves most of the queue's state
behind, and some of its jobs later come back on the deleted queue by
themselves. The problem statement is an incident report from an operator: it
names some of the effects, leaves the rest to be found, and fixes three
behaviours that must not change.

The reference fix scores 1.0 on every criterion, and the unchanged repository
scores 0.0. Before the task was packaged, its grader was run on a ladder of
control patches, from a comment-only change to a second correct design and a
cheat, and five agent runs were graded.

## Uses

### Direct Use

- Evaluating coding agents on a repository-level task: give the agent
  `problem_statement` and a checkout of `repo` at `base_commit`, then score the
  resulting diff with the task's grader.
- Running the task end to end with Harbor, from the `harbor/` folder (see
  [Running the task](#running-the-task)).
- Building or validating graders and task-quality tooling, using the reference
  fix, the hidden checks and the weighted criteria together.

## Dataset Structure

One split, `test`, with one row. The columns are those of the EC-SWE release.

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
| `grader` | list of (criterion, weight) | the grader's criteria and their weights in percent; weights add up to 100 |
| `grader_files` | list of (path, encoding, content) | the grader as built into the verifier image (`tests/`): one program per criterion and their shared harness, the list of repository tests that pass at `base_commit`, the criteria and weights (`config.json`), and the scripts that score a run (`verify.py`, `test.sh`) |
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
- **Criteria:** 9: 6 targets and 3 fences, 2 of the fences blockers
- **Reference fix:** `rq/queue.py` (one method changed, three helpers added) and a new test file, 228 lines added
- **Model of the graded agent runs:** claude-opus-5-5

### Difficulty

Difficulty is the mean reward of the graded agent runs: five runs of
claude-opus-5-5 at effort max, each with a 30-minute agent limit, graded by the
task's verifier.

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

## Running the task

The `harbor/` folder of this repository makes the task runnable end to end with
[Harbor](https://github.com/harbor-framework/harbor) 0.26.0 and Docker. The
task is packaged as two containers: one for the agent, holding the repository
at its base commit and nothing from the grading side, and a separate one that
grades the patch the agent leaves behind. Both are offline, except that the
agent reaches its model's API. The folder holds the task's complete build
context, so both images can be rebuilt from this repository alone.

```bash
cd harbor
pip install harbor==0.26.0
python verify_bundle.py
harbor run -p tasks/rq_delete_queue_owned_state_contract -a oracle     # the reference fix: reward 1.0
harbor run -p tasks/rq_delete_queue_owned_state_contract -a nop        # no change: reward 0.0
harbor run -p tasks/rq_delete_queue_owned_state_contract -a <agent> -m <model> --env-file <file with the model API key>
```

`harbor/README.md` has the requirements, says how a score is produced, and maps
the task folder to its `instance_id` here. The folder contains the reference
fix and the hidden grader, as the row of this dataset does.

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
no change (0.00), a comment only (0.00), a shallow fix (0.35), a careful but
incomplete fix (0.70), a second correct design (1.00), and a cheat that
special-cases queue names and tries to write reward files (0.00). The ladder is
in `harbor/evidence/rq/author-calibration.txt`. The agent runs were graded by
the same verifier image.

#### Who are the source data producers?

The code comes from the rq project, written by its contributors. The problem
statement, reference fix, checks and grader are by Sriya Jonnadula.

### Annotations

#### Annotation process

The criteria and weights were written by the task's author. The difficulty
fields come from graded agent runs, not from people.

#### Who are the annotators?

The task's author.

#### Personal and Sensitive Information

The task is about source code. The names in the problem statement are
invented. Upstream code can contain contributor names in comments, licence
headers or metadata, as it does in the upstream repository.

## Recommendations

Report full solves alongside mean reward, and give the model's training cutoff
relative to this dataset's release (2026-11-20).

## Citation

**BibTeX:**

```bibtex
@misc{jonnadula2026rqdelete,
  author       = {Jonnadula, Sriya},
  title        = {{rq queue deletion}},
  year         = {2026},
  publisher    = {GitHub},
  howpublished = {\url{https://github.com/sriyaj007/rq-delete-queue-task}}
}
```

**APA:**

Jonnadula, S. (2026). *rq queue deletion* [Data set]. GitHub.
https://github.com/sriyaj007/rq-delete-queue-task

## Glossary

- **Gold run:** the task run with the reference fix applied. It must score 1.0.
- **Base run:** the task run on the unchanged repository. It should score low.
- **Reward:** the grader's weighted score for one run, 0 to 1.
- **Target:** a criterion for behaviour the unchanged code lacks.
- **Fence:** a criterion for behaviour the unchanged code already has. Fences
  pay only when at least one target passes.
- **Blocker:** a criterion whose failure caps the reward at 0.6.

## Dataset Card Authors

Sriya Jonnadula

## Dataset Card Contact

Sriya Jonnadula, through GitHub (`sriyaj007`).
