#!/bin/bash
# bootstrap_setup.sh - Trigger setup with environment variables
if [ -f "/workspace/.env" ]; then
    echo "Loading .env variables..."
    export $(grep -v '^#' /workspace/.env | xargs)
fi
echo "Starting setup_hunyuan.py..."
python3 /workspace/setup_hunyuan.py
