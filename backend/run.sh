#!/usr/bin/env bash
set -euo pipefail

# Simple start/stop/status helper for the backend
# Usage: ./run.sh start|stop|status

ROOT_DIR=$(cd "$(dirname "$0")"/.. && pwd)
BACKEND_DIR="$ROOT_DIR/backend"
PIDFILE="$BACKEND_DIR/uvicorn.pid"
LOGFILE="$BACKEND_DIR/uvicorn.log"

start() {
  if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "Backend already running (pid=$(cat $PIDFILE))"
    return 0
  fi

  echo "Starting backend..."
  mkdir -p "$BACKEND_DIR"
  # ensure .env is loaded by uvicorn via environment; user should create backend/.env from .env.example
  nohup env $(cat "$BACKEND_DIR/.env" 2>/dev/null || true) \
    PYTHONPATH="$ROOT_DIR" python3.11 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  echo "Started (pid=$(cat $PIDFILE)). Logs: $LOGFILE"
}

stop() {
  if [ ! -f "$PIDFILE" ]; then
    echo "No pidfile found, not running?"
    return 0
  fi
  PID=$(cat "$PIDFILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping pid $PID..."
    kill "$PID"
    sleep 1
    rm -f "$PIDFILE"
    echo "Stopped"
  else
    echo "Process $PID not running. Removing stale pidfile."
    rm -f "$PIDFILE"
  fi
}

status() {
  if [ -f "$PIDFILE" ] && kill -0 "$(cat $PIDFILE)" 2>/dev/null; then
    echo "Running (pid=$(cat $PIDFILE))"
  else
    echo "Not running"
  fi
}

case ${1-} in
  start) start ;; 
  stop) stop ;; 
  status) status ;; 
  *) echo "Usage: $0 start|stop|status"; exit 2 ;;
esac
