#!/bin/bash
# Verifier entry point. Runs as root in the separate, offline verifier
# container. The reward is the weighted score written by verify.py.
set -u

mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json /logs/verifier/report.json /logs/verifier/ctrf.json

# Candidate code runs as uid 1000. Close the reward folder and /logs itself
# (Docker Desktop does not enforce the mode of a bind mount against other
# users; /logs is the container's own folder) before any of it runs. This
# also hides /logs/artifacts, which Harbor copies from the agent's
# container: only the captured patch is graded.
chmod 700 /logs/verifier
chmod 700 /logs

python3 -I /tests/verify.py
status=$?

# The harness reads reward.json before reward.txt. Only reward.txt is ours.
rm -f /logs/verifier/reward.json
if [ "$status" -ne 0 ]; then
  rm -f /logs/verifier/reward.txt
  echo "verify.py failed with status $status; no reward written" >&2
  exit "$status"
fi
