#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Start the authorization server on port 9000 in the background
echo "----> Starting auth server on port 9000..."
uvicorn server:app --host 0.0.0.0 --port 9000 &

# Start the main API server on port 8000 in the foreground
# The 'exec' command replaces the shell process with the uvicorn process,
# allowing it to receive signals correctly for graceful shutdown.
echo "----> Starting main API server on port 8000..."
exec uvicorn api_server:app --host 0.0.0.0 --port 8000
