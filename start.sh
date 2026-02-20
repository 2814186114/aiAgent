#!/bin/bash

export PYTHON_PORT=8000
export NODE_PORT=3001

node server.js &

uvicorn main:app --host 0.0.0.0 --port ${PYTHON_PORT} &

wait
