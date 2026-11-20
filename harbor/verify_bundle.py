"""Check every file in this folder against checksums.json before building anything."""

import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
expected = json.loads((root / "checksums.json").read_text())
problems = []
for name, digest in sorted(expected.items()):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise SystemExit(f"Unsafe path in checksums.json: {name}")
    if not path.is_file():
        problems.append(f"missing: {name}")
    elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        problems.append(f"changed: {name}")
listed = set(expected) | {"checksums.json"}
for path in sorted(root.rglob("*")):
    name = path.relative_to(root).as_posix()
    if path.is_file() and name not in listed and "__pycache__" not in path.parts:
        problems.append(f"not in checksums.json: {name}")
if problems:
    print("\n".join(problems))
    sys.exit(1)
print(f"Validated {len(expected)} file checksums")
