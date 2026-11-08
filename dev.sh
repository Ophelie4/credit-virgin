#!/usr/bin/env bash
# Start backend (port 8000) and frontend (port 5173) together. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

if ! grep -q "^GEMINI_API_KEY=.\+" backend/.env 2>/dev/null; then
  echo "backend/.env is missing GEMINI_API_KEY. Edit it first."; exit 1
fi

(cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
BACK=$!
(cd frontend && npm run dev -- --host) &
FRONT=$!
trap 'kill $BACK $FRONT 2>/dev/null' EXIT INT TERM

sleep 2
echo
echo "  App:  http://localhost:5173"
echo "  API:  http://localhost:8000/api/health"
echo
wait
