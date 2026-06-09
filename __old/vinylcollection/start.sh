#!/bin/bash
# Vinyl Collection Dashboard — terminal launcher
cd "$(dirname "$0")"
python3 -m pip install --quiet flask requests
python3 run.py "$@"
