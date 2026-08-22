#!/usr/bin/env bash
# Security checks for GenMail: dependency vulnerabilities (Python + JS) and a
# static analysis pass over the server code. Run from anywhere:
#   ./security_check.sh
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "== Python dependency audit (pip-audit) =="
( cd "$ROOT/server" && uv run --with pip-audit pip-audit ) || true

echo
echo "== Python static analysis (bandit) =="
( cd "$ROOT/server" && uv run --with bandit bandit -r . -x ./.venv -q ) || true

echo
echo "== JS dependency audit (npm audit) =="
( cd "$ROOT/client" && npm audit ) || true
