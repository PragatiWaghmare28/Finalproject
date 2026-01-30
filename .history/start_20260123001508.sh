#!/usr/bin/env bash
set -euo pipefail

# Build frontend and start backend (uses python3.11)
ROOT_DIR=$(dirname "$0")

echo "Building frontend..."
cd "$ROOT_DIR/video-rag-app"
npm install
npm run build

echo "Starting backend..."
cd "$ROOT_DIR/backend"
PYTHONPATH=. python3.11 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
