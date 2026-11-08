#!/usr/bin/env bash
# One-time setup. Run from the project root:  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "== Checking tools"
for c in python3 node npm git; do
  command -v "$c" >/dev/null || { echo "Missing: $c"; exit 1; }
  printf "  %-8s %s\n" "$c" "$($c --version 2>&1 | head -1)"
done

echo "== Backend"
cd backend
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "  created backend/.env  <-- paste your keys in here"; }
cd ..

echo "== Frontend"
cd frontend
npm install --silent
[ -f .env ] || cp .env.example .env
cd ..

echo
echo "Done. Next:"
echo "  1. Edit backend/.env: set TIMESCALE_SERVICE_URL and GEMINI_API_KEY"
echo "  2. bash dev.sh"
