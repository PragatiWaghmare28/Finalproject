#!/usr/bin/env bash
set -euo pipefail

# Build frontend and start backend (uses python3.11)
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "Building frontend..."
npm_dir="$ROOT_DIR/video-rag-app"
if [ ! -d "$npm_dir" ]; then
	echo "Error: frontend directory not found: $npm_dir" >&2
	exit 1
fi
cd "$npm_dir"
npm install
npm run build

echo "Starting backend..."
backend_dir="$ROOT_DIR/backend"
if [ ! -d "$backend_dir" ]; then
	echo "Error: backend directory not found: $backend_dir" >&2
	exit 1
fi
cd "$backend_dir"
# Ensure repo root is on PYTHONPATH so `backend` package is importable
PYTHONPATH="$ROOT_DIR" python3.11 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
