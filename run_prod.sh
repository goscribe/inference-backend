#!/bin/bash
# Production startup script for Scribe Inference Backend

# Change to script directory
cd "$(dirname "$0")"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Production settings
WORKERS=${WORKERS:-4}
PORT=${PORT:-61016}
TIMEOUT=${TIMEOUT:-300}
BIND=${BIND:-0.0.0.0:$PORT}

# Run with Gunicorn
echo "Starting Scribe Inference Backend in PRODUCTION mode..."
echo "Workers: $WORKERS"
echo "Port: $PORT"
echo "Timeout: $TIMEOUT seconds"
echo "Bind: $BIND"

gunicorn \
    --workers $WORKERS \
    --bind $BIND \
    --timeout $TIMEOUT \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    --preload \
    app.main:app



