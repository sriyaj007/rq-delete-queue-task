"""Write the agent's change as one patch against the baseline commit.

Runs as root after the agent finishes, before the separate verifier starts.

First it stops every process the agent left running (uid 1000). Harbor keeps
this container up until verification is over, and its /logs/verifier is the
same host folder the verifier writes to, so a leftover process could
otherwise rewrite the reward after the verifier has written it.

Then it uses the root-owned copy of the baseline history, so hooks, config or
refs the agent left in the checkout's own .git have no effect. New files are
included; files ignored by the repository's .gitignore are not.
"""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

AGENT_UID = "1000"


def agent_processes():
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            status = (entry / "status").read_text()
        except OSError:
            continue
        fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
        uid = fields.get("Uid", "").split()[:1]
        state = fields.get("State", "").strip()[:1]
        # Process 1 is the container's own idle command, which nothing inside
        # the container can signal; killed processes stay listed as zombies
        # (Z) until reaped. Neither can run any code.
        if uid == [AGENT_UID] and entry.name != "1" and state not in ("Z", "X"):
            found.append(int(entry.name))
    return found


def describe(pid):
    try:
        state = next(l for l in Path(f"/proc/{pid}/status").read_text().splitlines() if l.startswith("State:"))
        args = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        return f"{pid} {state.split(':', 1)[1].strip()} {args[:120]}"
    except OSError:
        return str(pid)


def stop_agent_processes():
    # Stop them all first so none can fork while the others are killed, then
    # give the kernel time to finish tearing them down: a large process (a
    # test run, say) can take well over a second to exit after SIGKILL.
    deadline = time.monotonic() + 60
    while True:
        pids = agent_processes()
        if not pids:
            return
        if time.monotonic() > deadline:
            raise SystemExit("could not stop the agent's processes: " + "; ".join(describe(p) for p in pids))
        for sig in (signal.SIGSTOP, signal.SIGKILL):
            for pid in pids:
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
        time.sleep(0.2)


stop_agent_processes()
for name in ("reward.txt", "reward.json"):
    try:
        os.unlink(f"/logs/verifier/{name}")
    except OSError:
        pass

REPO = Path("/workspace/repo")
OUT = Path("/workspace/submissions/submitted.patch")
MAX_BYTES = 32 * 1024 * 1024

with tempfile.TemporaryDirectory(prefix="capture-") as tmp:
    git_dir = Path(tmp) / "git"
    shutil.copytree("/opt/task-tools/baseline.git", git_dir)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": tmp,
        "GIT_DIR": str(git_dir),
        "GIT_WORK_TREE": str(REPO),
        "GIT_INDEX_FILE": str(Path(tmp) / "index"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], env=env, text=True).strip()
    subprocess.run(["git", "read-tree", base], env=env, check=True)
    subprocess.run(["git", "add", "--all", "--", "."], env=env, check=True, cwd=REPO)
    patch = subprocess.check_output(
        ["git", "diff", "--cached", "--binary", "--full-index", "--no-renames",
         "--no-ext-diff", "--no-textconv", "--no-color", base],
        env=env, cwd=REPO,
    )
    if len(patch) > MAX_BYTES:
        # Graded as no change, rather than left missing (which is an error).
        print(f"submission is larger than {MAX_BYTES} bytes; recording it as empty")
        patch = b""
    # The agent can write in the submissions folder. Whatever it left at the
    # submission path is replaced; the patch is written in a root-only folder
    # first and moved into place.
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.is_symlink() or OUT.is_file():
        OUT.unlink()
    elif OUT.exists():
        shutil.rmtree(OUT)
    staging = Path(tempfile.mkdtemp(prefix=".capture-", dir="/workspace"))
    (staging / "submitted.patch").write_bytes(patch)
    os.replace(staging / "submitted.patch", OUT)
    staging.rmdir()
    print(json.dumps({"bytes": len(patch), "sha256": hashlib.sha256(patch).hexdigest(), "base_commit": base}))
