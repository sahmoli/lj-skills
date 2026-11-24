#!/usr/bin/env bash
# Explicit-profile installer. The Python backend also handles Windows junctions safely.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${PYTHON_BIN:-}" ]; then
  if command -v python3 >/dev/null 2>&1; then PYTHON_BIN=python3
  elif command -v python >/dev/null 2>&1; then PYTHON_BIN=python
  else echo "Python 3 is required (or set PYTHON_BIN)" >&2; exit 127
  fi
fi
exec "$PYTHON_BIN" "$REPO/scripts/install_skills.py" "$@"
