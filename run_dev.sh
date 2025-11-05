#!/bin/bash
# Development startup script for Scribe Inference Backend

# Change to script directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run in development mode
echo "Starting Scribe Inference Backend in DEVELOPMENT mode..."
python -m app.main

