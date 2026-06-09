#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  DuckDuckVinyl – build script (macOS / Linux)
#  Run this from the project root directory.
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "[1/4] Checking Python..."
python3 --version

echo "[2/4] Installing build dependencies..."
pip3 install pyinstaller requests flask

echo "[3/4] Cleaning previous build artefacts..."
rm -rf build dist

echo "[4/4] Building binary with PyInstaller..."
pyinstaller duckduckvinyl.spec

echo ""
echo "══════════════════════════════════════════════════════════════"
echo " BUILD SUCCESSFUL"
echo " Your binary is at:  dist/DuckDuckVinyl"
echo "══════════════════════════════════════════════════════════════"
