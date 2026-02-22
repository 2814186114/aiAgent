#!/bin/bash

cd /app

export PYTHON_HOST=127.0.0.1
export PYTHON_PORT=8000
export NODE_PORT=3001

echo "Starting Python server on $PYTHON_HOST:$PYTHON_PORT..."
uvicorn main:app --host 127.0.0.1 --port $PYTHON_PORT 2>&1 &
PYTHON_PID=$!

sleep 5

echo "Starting Node.js server..."
node server.js 2>&1 &
NODE_PID=$!

sleep 2

echo "Starting Nginx on port ${PORT:-8080}..."
nginx -g 'daemon off;' &
NGINX_PID=$!

wait $PYTHON_PID $NODE_PID $NGINX_PID
