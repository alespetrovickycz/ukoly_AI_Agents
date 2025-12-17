# Wazuh Incident Analysis System

AI-powered system for analyzing Wazuh security incidents from OpenSearch and generating comprehensive PDF reports with visualizations and AI-generated recommendations.

## Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  OpenSearch     │◄─────│  MCP Server     │◄─────│ LangChain Agent │
│  (Wazuh data)   │      │  (Port 8002)    │      │   + Ollama      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                            │
                                                            ▼
                                                   ┌─────────────────┐
                                                   │  PDF Generator  │
                                                   │  (Czech reports)│
                                                   └─────────────────┘
```

## Features

- ✅ **MCP Server** - HTTP-based Model Context Protocol server for OpenSearch queries
- ✅ **Date-based Index Pattern** - Automatic handling of `wazuh-alerts-4.x-YYYY.MM.DD` indices
- ✅ **Smart Aggregations** - Fast statistics using OpenSearch aggregations
- ✅ **LangChain Integration** - Agent framework with MCP tool support
- ✅ **Ollama via LiteLLM** - Local llama3 model through LiteLLM proxy (Docker)
- ✅ **Czech Language** - Reports and recommendations in Czech
- ✅ **Rich Visualizations** - Timeline, severity distribution, regional analysis, top incidents
- ✅ **AI Recommendations** - Strategic and tactical security recommendations
- ✅ **Configurable** - Sample size, output directory, logo customization

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- [Ollama](https://ollama.ai/) with llama3 model
- Docker and Docker Compose (for LiteLLM)
- Access to OpenSearch instance with Wazuh data

## Installation

### 1. Install Ollama and llama3

```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull llama3 model
ollama pull llama3
```

### 2. Setup LiteLLM Proxy (Docker)

```bash
cd wazuh_agent

# Start LiteLLM with Docker Compose
docker-compose up -d

# Verify LiteLLM is running
curl http://localhost:4000/health

# Test connection to Ollama
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy-key" \
  -d '{
    "model": "ollama-llama3",
    "messages": [{"role": "user", "content": "Ahoj"}]
  }'
```

You should see a Czech response from llama3.

### 3. Configure Environment Variables

Create `.env` files for both MCP server and agent:

**MCP Server** (`mcp_server/.env`):
```bash
OPENSEARCH_HOST=your-opensearch-host
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your-password
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false
```

**Agent** (`agent/.env`):
```bash
WAZUH_MCP_URL=http://localhost:8002/mcp
LITELLM_BASE_URL=http://localhost:4000
LITELLM_API_KEY=dummy-key
MAX_INCIDENTS_SAMPLE=1000
REPORT_OUTPUT_DIR=./reports
COMPANY_LOGO_PATH=../logo-full-color-cropped.png
```

## Usage

### Start the System

**Terminal 1: Start MCP Server**
```bash
cd wazuh_agent/mcp_server
uv run uvicorn server:starlette_app --host 0.0.0.0 --port 8002
```

You should see:
```
INFO:     Wazuh MCP Server started with StreamableHTTP session manager!
INFO:     Server listening on http://0.0.0.0:8002/mcp
```

**Terminal 2: Run Analysis Agent**
```bash
cd wazuh_agent/agent
uv run python main.py
```

**Alternative: Using helper scripts**
```bash
# Terminal 1
cd wazuh_agent/mcp_server
./run.sh

# Terminal 2
cd wazuh_agent/agent
./run.sh
```

The agent will:
1. Connect to MCP server
2. Query last 7 days of Wazuh incidents from OpenSearch
3. Analyze patterns using llama3
4. Generate strategic and tactical recommendations
5. Create a PDF report with visualizations

### Output

PDF report will be saved to `wazuh_agent/reports/wazuh_report_YYYYMMDD_HHMMSS.pdf`

## Report Contents

The generated Czech PDF report includes:

### 1. Executive Summary
- Total incidents count
- Daily average
- Critical incidents (level ≥10)
- Most affected region
- Top incident type

### 2. Visualizations
- **Timeline Chart** - Daily incident trend over 7 days
- **Severity Distribution** - Bar chart with color-coded levels (green/yellow/red)
- **Top 10 Incident Types** - Horizontal bar chart
- **Regional Distribution** - Pie chart showing geographic patterns
- **Top 10 Servers** - Most affected agents/servers
- **Top 10 Decoders** - Most triggered log decoders

### 3. AI-Generated Recommendations

**Strategická doporučení** (Strategic):
- High-level security strategy direction
- Long-term measures
- Priority areas

**Taktická/technická doporučení** (Tactical):
- Specific technical measures
- Firewall rules, WAF configurations
- Security rule tuning suggestions
- Server-specific actions

## Project Structure

```
wazuh_agent/
├── mcp_server/                 # MCP Server (OpenSearch tool)
│   ├── server.py              # HTTP MCP server
│   ├── tools/
│   │   ├── __init__.py
│   │   └── opensearch_tool.py # OpenSearch query implementation
│   ├── pyproject.toml
│   └── .env
├── agent/                      # LangChain Agent
│   ├── main.py                # Agent orchestrator
│   ├── analyzer.py            # Data processing & statistics
│   ├── pdf_generator.py       # Czech PDF reports with charts
│   ├── pyproject.toml
│   └── .env
├── reports/                    # Generated PDF reports
├── logo-full-color-cropped.png # Company logo
├── docker-compose.yml         # LiteLLM Docker setup
├── litellm_config.yaml        # LiteLLM configuration
├── .env.example               # Example environment variables
└── README_SETUP.md            # This file
```

## Configuration Options

### Environment Variables

**MAX_INCIDENTS_SAMPLE** (default: 1000)
- Maximum number of incident samples to fetch for detailed analysis
- Higher values = more data but slower processing

**REPORT_OUTPUT_DIR** (default: `./reports`)
- Directory where PDF reports will be saved

**COMPANY_LOGO_PATH** (default: `./logo-full-color-cropped.png`)
- Path to company logo for report header

### OpenSearch Index Pattern

The system automatically generates index patterns for the last 7 days:
```
wazuh-alerts-4.x-2025.11.21,wazuh-alerts-4.x-2025.11.22,...,wazuh-alerts-4.x-2025.11.28
```

Missing indices are automatically ignored by OpenSearch.

## Troubleshooting

### MCP Server won't start

**Error**: `ModuleNotFoundError: No module named 'mcp'`

**Solution**:
```bash
cd wazuh_agent/mcp_server
uv sync  # Install dependencies
uv run uvicorn server:starlette_app --port 8002
```

### Agent can't connect to MCP server

**Error**: `Connection refused to http://localhost:8002/mcp`

**Solution**: Ensure MCP server is running in another terminal

### OpenSearch connection fails

**Error**: `ConnectionError` or `AuthenticationException`

**Solution**: Check your OpenSearch credentials in `mcp_server/.env`
```bash
# Test connection manually
curl -u admin:password http://your-opensearch-host:9200/_cat/indices
```

### LiteLLM not responding

**Error**: `Connection refused to http://localhost:4000`

**Solution**:
```bash
# Check if container is running
docker ps | grep litellm

# Restart if needed
docker-compose restart

# Check logs
docker logs litellm-proxy
```

### Ollama model not found

**Error**: `Model 'llama3' not found`

**Solution**:
```bash
# Pull the model
ollama pull llama3

# Verify it's available
ollama list
```

### PDF generation fails

**Error**: `PIL cannot identify image file`

**Solution**: Ensure logo file exists and is a valid PNG:
```bash
ls -lh wazuh_agent/logo-full-color-cropped.png
file wazuh_agent/logo-full-color-cropped.png
```

## Data Flow

1. **Agent** calls MCP server's `search_wazuh_incidents` tool
2. **MCP Server** queries OpenSearch with date-based indices
3. **OpenSearch** returns aggregations + sample incidents
4. **Agent** receives structured JSON data
5. **Analyzer** parses aggregations and calculates statistics
6. **LLM** (llama3 via LiteLLM) analyzes patterns and generates recommendations
7. **PDF Generator** creates visualizations and assembles Czech report

## Performance

- **Small deployment** (<10k incidents/week): < 1 minute
- **Medium deployment** (10k-100k): 1-3 minutes
- **Large deployment** (>100k): Consider increasing `MAX_INCIDENTS_SAMPLE` gradually

Aggregations are very efficient - most time is spent in LLM analysis.

## Security Notes

- All credentials stored in `.env` files (not committed to git)
- `.env` files are in `.gitignore`
- LiteLLM proxy uses dummy key (adequate for localhost)
- For production: use proper authentication and HTTPS

## Customization

### Change Report Language

Edit agent system prompt in `agent/main.py`:
```python
system_prompt="""You are a cybersecurity expert...
Write all responses in English."""  # Change to English
```

### Adjust Analysis Depth

Modify `MAX_INCIDENTS_SAMPLE` in `agent/.env`:
```bash
MAX_INCIDENTS_SAMPLE=5000  # More samples for deeper analysis
```

### Add Custom Charts

Edit `agent/pdf_generator.py` to add new visualization functions.

### Change Date Range

Modify the agent query in `agent/main.py`:
```python
# Change from 7 days to 30 days
content=f"Vyhledej Wazuh incidenty za posledních 30 dní..."
```

Also update the tool call to use `days=30` parameter.

## License

Proprietary - Takmento

## Support

For issues or questions, contact the development team.
