#!/bin/bash
# Simple run script for Wazuh Agent

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
pip install langchain langchain-openai langchain-mcp-adapters python-dotenv reportlab matplotlib pandas seaborn Pillow

# Run agent
echo "Starting Wazuh Analysis Agent..."
python main.py
