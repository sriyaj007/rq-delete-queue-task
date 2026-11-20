#!/bin/bash
# Reference solution: apply the reference change to the checkout.
set -euo pipefail
cd /workspace/repo
git apply --whitespace=nowarn "$(dirname "$0")/reference.patch"
