#!/bin/bash

cd /app

export PYTHON_PORT=8000
export NODE_PORT=3001
export PORT=${PORT:-8080}

node server.js > /var/log/node.log 2>&1 &
echo "Node.js server started on port $NODE_PORT"

uvicorn main:app --host 0.0.0.0 --port $PYTHON_PORT > /var/log/python.log 2>&1 &
echo "Python server started on port $PYTHON_PORT"

sleep 3

nginx -g 'daemon off;'
