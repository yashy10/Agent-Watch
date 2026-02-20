#!/bin/bash
# Run Agent Watch with Datadog LLM Observability enabled (using uvicorn)

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set Datadog LLM Observability environment variables
export DD_LLMOBS_ENABLED=1
export DD_LLMOBS_ML_APP=agent-watch
export DD_SITE=${DD_SITE:-us5.datadoghq.com}

# Use DD_API_KEY from environment or .env file
if [ -z "$DD_API_KEY" ]; then
    echo "Error: DD_API_KEY not set. Please set it in .env or as an environment variable."
    exit 1
fi

PORT=${PORT:-8002}

echo "🛡️  Starting Agent Watch with Datadog LLM Observability..."
echo "   DD_API_KEY: ${DD_API_KEY:0:10}..."
echo "   DD_SITE: $DD_SITE"
echo "   ML_APP: $DD_LLMOBS_ML_APP"
echo "   Port: $PORT"
echo ""

# Run uvicorn with ddtrace-run
ddtrace-run python3 -m uvicorn server:app --host 0.0.0.0 --port $PORT
