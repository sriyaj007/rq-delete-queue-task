"""Fence. The repository's own test files are unchanged, and every test that
passes on the untouched code still passes."""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from _harness import check

HERE = Path(__file__).resolve().parent
JUNIT = Path.home() / "junit.xml"


def main(r):
    changed = subprocess.run(
        ["git", "diff", "--name-status", "HEAD", "--", "tests"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert not changed, f"existing test files were changed or deleted:\n{changed}"

    r.flushall()
    # The repository's tests read REDIS_* variables themselves; give them the
    # environment they get on a developer machine.
    env = {key: value for key, value in os.environ.items() if not key.startswith("REDIS")}
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-c", str(HERE / "rq-pytest.ini"), "--rootdir", ".",
         "-p", "no:cacheprovider", "-q", f"--junitxml={JUNIT}", "tests"],
        capture_output=True, text=True, env=env,
    )
    print(completed.stdout[-3000:])
    passed = set()
    for case in ET.parse(JUNIT).getroot().iter("testcase"):
        if not any(child.tag in ("failure", "error", "skipped") for child in case):
            passed.add(f"{case.get('classname')}::{case.get('name')}")
    expected = [line for line in (HERE / "baseline_passed.txt").read_text().splitlines() if line]
    lost = [test for test in expected if test not in passed]
    assert not lost, f"{len(lost)} tests that pass on the untouched code no longer pass, e.g. {lost[:10]}"


check(main)
