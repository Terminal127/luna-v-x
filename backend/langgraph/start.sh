#!/bin/sh
set -e

cleanup() {
    echo "----> Stopping all servers..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

echo "----> Starting auth server on port 9000..."
uvicorn server:app --host 0.0.0.0 --port 9000 &

echo "----> Starting backend server on port 8001..."
uvicorn thoughts_server:app --host 0.0.0.0 --port 8001 --reload &

echo "----> Starting main API server on port 8000..."
uvicorn api_server:app --host 0.0.0.0 --port 8000 &

# Wait for all background processes
wait
