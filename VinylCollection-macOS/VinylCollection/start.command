#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Vinyl Collection Dashboard — macOS launcher
# Double-click this file to start the app.
# ─────────────────────────────────────────────────────────────────

# Move to the folder where this script lives
cd "$(dirname "$0")"

# ── Check Python ────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  osascript -e 'display alert "Python 3 not found" message "Please install Python 3 from https://www.python.org/downloads/ and try again." as critical'
  exit 1
fi

PY=$(command -v python3)
echo "Using Python: $PY ($($PY --version))"

# ── Install / upgrade dependencies ──────────────────────────────
echo "Checking dependencies..."
$PY -m pip install --quiet --upgrade flask requests

# ── Launch ──────────────────────────────────────────────────────
echo "Starting Vinyl Collection Dashboard..."
$PY run.py
