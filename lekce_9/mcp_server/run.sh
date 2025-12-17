#!/bin/bash
# Simple run script for MCP server

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install mcp>=1.3.0 opensearch-py>=2.4.0 uvicorn>=0.27.0 starlette>=0.36.0 python-dotenv>=1.0.0

# Run server
echo "Starting Wazuh MCP Server..."
python -m uvicorn server:starlette_app --host 0.0.0.0 --port 8002
