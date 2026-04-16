#!/usr/bin/env bash
# run-local.sh — Start the full Johor Election Monitor stack locally.
# Requires: Python 3.12+, a running PostgreSQL and Redis (or Docker).
# Usage: ./run-local.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Load env vars
if [[ -f .env ]]; then
  set -a; source .env; set +a
else
  echo "ERROR: .env not found — copy .env.template to .env and fill in values"
  exit 1
fi

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

# Helper: start a service in the background
start_service() {
  local name="$1"; shift
  echo "▶  Starting $name..."
  "$@" > "$LOG_DIR/${name}.log" 2>&1 &
  echo $! > "$LOG_DIR/${name}.pid"
  echo "   PID $(cat "$LOG_DIR/${name}.pid") — logs: logs/${name}.log"
}

# Helper: wait until an HTTP endpoint responds
wait_for() {
  local name="$1" url="$2"
  echo -n "   Waiting for $name at $url ..."
  for i in $(seq 1 30); do
    if curl -sf "$url" > /dev/null 2>&1; then
      echo " ok"
      return 0
    fi
    sleep 1
    echo -n "."
  done
  echo " TIMEOUT"
  return 1
}

# ------------------------------------------------------------------
# 1. Control plane
# ------------------------------------------------------------------
start_service control_plane \
  uvicorn control_plane.server:app --host 0.0.0.0 --port "${CONTROL_PLANE_PORT:-8000}" --reload

wait_for "control_plane" "http://localhost:${CONTROL_PLANE_PORT:-8000}/health"

# ------------------------------------------------------------------
# 2. Agents (started in dependency order)
# ------------------------------------------------------------------
start_service wiki_agent \
  uvicorn agents.wiki_agent.server:app --host 0.0.0.0 --port 8005 --reload

start_service news_agent \
  uvicorn agents.news_agent.server:app --host 0.0.0.0 --port 8001 --reload

start_service scorer_agent \
  uvicorn agents.scorer_agent.server:app --host 0.0.0.0 --port 8002 --reload

start_service analyst_agent \
  uvicorn agents.analyst_agent.server:app --host 0.0.0.0 --port 8003 --reload

start_service seat_agent \
  uvicorn agents.seat_agent.server:app --host 0.0.0.0 --port 8004 --reload

# Brief pause so agents can register
sleep 2

# ------------------------------------------------------------------
# 3. Dashboard
# ------------------------------------------------------------------
if [[ -d "$ROOT/dashboard" && -f "$ROOT/dashboard/package.json" ]]; then
  start_service dashboard \
    bash -c "cd '$ROOT/dashboard' && npm run dev -- --port 5173 --host"
  echo ""
  echo "  Dashboard: http://localhost:5173"
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Johor Election Monitor running"
echo "  Control plane : http://localhost:${CONTROL_PLANE_PORT:-8000}"
echo "  Graph         : http://localhost:${CONTROL_PLANE_PORT:-8000}/graph"
echo "  Wiki agent    : http://localhost:8005"
echo "  News agent    : http://localhost:8001"
echo "  Scorer agent  : http://localhost:8002"
echo "  Analyst agent : http://localhost:8003"
echo "  Seat agent    : http://localhost:8004"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Logs in: $LOG_DIR"
echo "  To stop: kill \$(cat logs/*.pid)"
echo ""

# Keep script alive so Ctrl-C kills the whole group
wait
