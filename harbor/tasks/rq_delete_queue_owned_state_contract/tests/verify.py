"""Grade one submission in a fresh, offline verifier container.

Steps:
1. Apply the captured patch to a pristine checkout of the baseline commit.
2. Run every criterion in config.json as its own program, as an unprivileged
   user, each with a fresh backing service when the task needs one.
   Exit status 0 means the behaviour holds, 1 means it does not.
3. Compute the weighted score: fence criteria (behaviour the untouched code
   already has) pay only when at least one target criterion passes, and a
   failed blocker caps the score.
4. Write ctrf.json and report.json, then reward.txt last.

Only this program, running as root, writes to /logs/verifier. Candidate code
runs as uid 1000 and cannot reach it.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

OUT = Path("/logs/verifier")
CONFIG = Path("/tests/config.json")
CHECKS = Path("/tests/checks")
PATCH = Path("/workspace/submissions/submitted.patch")
REPO = Path("/workspace/repo")
GRADER_UID = 1000
GRADER_HOME = Path("/tmp/grader-home")
MAX_PATCH_BYTES = 32 * 1024 * 1024


class InfrastructureError(RuntimeError):
    """The grader itself could not judge. No reward is published."""


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, **kwargs)


def kill_grader_processes() -> None:
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            status = (entry / "status").read_text()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        uid = next((line.split()[1] for line in status.splitlines() if line.startswith("Uid:")), None)
        if uid == str(GRADER_UID):
            try:
                os.kill(int(entry.name), signal.SIGKILL)
            except ProcessLookupError:
                pass


def as_grader(command: list[str], extra_env: dict[str, str] | None = None) -> list[str]:
    env = [
        "env", "-i",
        f"HOME={GRADER_HOME}",
        "PATH=/usr/local/bin:/usr/bin:/bin",
        "LANG=C.UTF-8",
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONUNBUFFERED=1",
        *(f"{key}={value}" for key, value in (extra_env or {}).items()),
    ]
    return ["setpriv", f"--reuid={GRADER_UID}", f"--regid={GRADER_UID}", "--clear-groups", "--no-new-privs", *env, *command]


def apply_patch(record: dict) -> str:
    if PATCH.is_symlink() or (PATCH.exists() and not PATCH.is_file()):
        record["patch_error"] = "submission is not a regular file"
        return "rejected"
    if not PATCH.exists():
        # The trusted capture step always writes this file, empty when nothing
        # changed. Missing means collection failed: not the agent's score.
        raise InfrastructureError("no submission was collected")
    if PATCH.stat().st_size == 0:
        return "empty"
    if PATCH.stat().st_size > MAX_PATCH_BYTES:
        record["patch_error"] = "submission is too large"
        return "rejected"
    checked = run(["git", "apply", "--check", str(PATCH)], cwd=REPO)
    if checked.returncode:
        record["patch_error"] = checked.stderr[-4000:]
        return "rejected"
    run(["git", "apply", str(PATCH)], cwd=REPO, check=True)
    changed = run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=REPO, check=True).stdout
    record["changed_files"] = changed.splitlines()
    return "applied" if changed.strip() else "empty"


def hand_checkout_to_grader() -> None:
    run(["chown", "-R", f"{GRADER_UID}:{GRADER_UID}", str(REPO)], check=True)
    shutil.rmtree(GRADER_HOME, ignore_errors=True)
    GRADER_HOME.mkdir(parents=True)
    os.chown(GRADER_HOME, GRADER_UID, GRADER_UID)


class Service:
    """A fresh backing service for one criterion, run as the grader user."""

    def __init__(self, kind: str | None):
        self.kind = kind
        self.process: subprocess.Popen | None = None

    def __enter__(self) -> dict[str, str]:
        if self.kind is None:
            return {}
        if self.kind != "redis":
            raise InfrastructureError(f"unknown service {self.kind}")
        data = GRADER_HOME / "redis-data"
        shutil.rmtree(data, ignore_errors=True)
        data.mkdir(parents=True)
        os.chown(data, GRADER_UID, GRADER_UID)
        self.process = subprocess.Popen(
            as_grader(["redis-server", "--port", "6379", "--bind", "127.0.0.1", "--save", "",
                       "--appendonly", "no", "--dir", str(data)]),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            if run(["redis-cli", "-p", "6379", "ping"]).stdout.strip() == "PONG":
                return {"REDIS_URL": "redis://127.0.0.1:6379/0"}
            time.sleep(0.1)
        raise InfrastructureError("redis-server did not start")

    def __exit__(self, *exc) -> None:
        kill_grader_processes()
        if self.process is not None:
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                raise InfrastructureError("redis-server did not stop")


def run_criterion(criterion: dict, service: str | None) -> dict:
    script = CHECKS / criterion["check"]
    started = time.monotonic()
    with Service(service) as service_env:
        command = as_grader([sys.executable, "-E", "-s", str(script)], service_env)
        try:
            completed = subprocess.run(
                command, cwd=REPO, text=True, capture_output=True, timeout=criterion["timeout"],
            )
            exit_code, output = completed.returncode, completed.stdout + completed.stderr
        except subprocess.TimeoutExpired as error:
            exit_code = None
            output = f"timed out after {criterion['timeout']} s\n" + (error.stdout or "") + (error.stderr or "")
    # Status 3 is the harness saying it could not reach its backing service,
    # which it checks before any code under test is imported. Status 3 without
    # that line came from the code under test, and counts as a failure.
    if exit_code == 3 and output.startswith("GRADER: "):
        raise InfrastructureError(f"{criterion['name']} could not judge: {output[-2000:]}")
    return {
        "name": criterion["name"],
        "passed": exit_code == 0,
        "exit_code": exit_code,
        "seconds": round(time.monotonic() - started, 2),
        "output": output[-4000:],
    }


def score(config: dict, results: dict[str, dict]) -> tuple[float, float, bool]:
    criteria = config["criteria"]
    progress = any(results[c["name"]]["passed"] for c in criteria if not c["fence"])
    raw = 0.0
    for c in criteria:
        if results[c["name"]]["passed"] and (progress or not c["fence"]):
            raw += c["weight"]
    capped = any(c["blocker"] and not results[c["name"]]["passed"] for c in criteria)
    reward = min(raw, config["blocker_cap"]) if capped else raw
    return round(raw, 6), round(reward, 6), capped


def write_ctrf(config: dict, results: dict[str, dict], started_ms: int) -> None:
    tests = []
    for c in config["criteria"]:
        r = results.get(c["name"])
        status = "skipped" if r is None else ("passed" if r["passed"] else "failed")
        tests.append({
            "name": c["name"],
            "status": status,
            "duration": int(1000 * (r or {}).get("seconds", 0)),
            "message": "" if r is None or r["passed"] else r["output"][-1000:],
            "extra": {"weight": c["weight"], "blocker": c["blocker"], "fence": c["fence"]},
        })
    summary = {
        "tests": len(tests),
        "passed": sum(t["status"] == "passed" for t in tests),
        "failed": sum(t["status"] == "failed" for t in tests),
        "pending": 0,
        "skipped": sum(t["status"] == "skipped" for t in tests),
        "other": 0,
        "start": started_ms,
        "stop": int(time.time() * 1000),
    }
    report = {"reportFormat": "CTRF", "specVersion": "0.0.0",
              "results": {"tool": {"name": config["task_id"] + " verify.py"}, "summary": summary, "tests": tests}}
    (OUT / "ctrf.json").write_text(json.dumps(report, indent=2) + "\n")


def main() -> None:
    started_ms = int(time.time() * 1000)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("reward.txt", "reward.json", "report.json", "ctrf.json"):
        (OUT / name).unlink(missing_ok=True)
    config = json.loads(CONFIG.read_text())
    weights = [c["weight"] for c in config["criteria"]]
    if not math.isclose(sum(weights), 1.0, abs_tol=1e-9):
        raise InfrastructureError("criterion weights do not sum to 1")

    record: dict = {"task_id": config["task_id"], "status": "error"}
    results: dict[str, dict] = {}
    try:
        status = apply_patch(record)
        record["status"] = status
        if status == "applied":
            hand_checkout_to_grader()
            for criterion in config["criteria"]:
                results[criterion["name"]] = run_criterion(criterion, config.get("service"))
            raw, reward, capped = score(config, results)
        else:
            raw, reward, capped = 0.0, 0.0, False
        record.update(raw_score=raw, reward=reward, blocker_cap_applied=capped,
                      criteria=[results.get(c["name"], {"name": c["name"], "passed": False, "not_run": True})
                                for c in config["criteria"]])
        write_ctrf(config, results, started_ms)
        (OUT / "report.json").write_text(json.dumps(record, indent=2) + "\n")
        (OUT / "reward.json").unlink(missing_ok=True)
        (OUT / "reward.txt").write_text(f"{reward}\n")
        print(f"status={status} raw={raw} reward={reward} blocker_cap_applied={capped}")
        for c in config["criteria"]:
            r = results.get(c["name"])
            mark = "not run" if r is None else ("PASS" if r["passed"] else "FAIL")
            print(f"  {mark:7} {c['weight']:.2f} {c['name']}")
    except BaseException as error:
        kill_grader_processes()
        (OUT / "reward.txt").unlink(missing_ok=True)
        (OUT / "reward.json").unlink(missing_ok=True)
        record.update(status="error", error=f"{type(error).__name__}: {error}")
        (OUT / "report.json").write_text(json.dumps(record, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
