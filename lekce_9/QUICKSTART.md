# Quick Start Guide

Rychlý průvodce pro spuštění Wazuh Incident Analysis systému.

## Předpoklady

- ✅ Python 3.10+
- ✅ uv package manager
- ✅ Ollama s llama3 modelem
- ✅ Docker a Docker Compose
- ✅ Přístup k OpenSearch instanci s Wazuh daty

## Instalace (5 minut)

### 1. Ollama Setup

```bash
# Start Ollama
ollama serve

# V novém terminálu: pull llama3
ollama pull llama3
```

### 2. LiteLLM Docker Setup

```bash
cd wazuh_agent

# Start LiteLLM
docker-compose up -d

# Test
curl http://localhost:4000/health
```

### 3. Konfigurace

Edituj `mcp_server/.env`:
```bash
OPENSEARCH_HOST=your-host
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your-password
```

Edituj `agent/.env` (obvykle není třeba měnit).

## Spuštění (2 terminály)

### Terminal 1: MCP Server

```bash
cd wazuh_agent/mcp_server
uv run uvicorn server:starlette_app --host 0.0.0.0 --port 8002
```

Čekej na:
```
INFO: Wazuh MCP Server started with StreamableHTTP session manager!
INFO: Server listening on http://0.0.0.0:8002/mcp
```

### Terminal 2: Agent

```bash
cd wazuh_agent/agent
uv run python main.py
```

**Alternativně** můžeš použít pomocné skripty:
```bash
# Terminal 1
cd wazuh_agent/mcp_server
./run.sh

# Terminal 2
cd wazuh_agent/agent
./run.sh
```

## Výsledek

PDF report bude v: `wazuh_agent/reports/wazuh_report_YYYYMMDD_HHMMSS.pdf`

## Časový průběh

```
🚀 Starting Wazuh Incident Analysis Agent...
📡 Connecting to Wazuh MCP server...
✅ Loaded 1 tools from MCP server
🤖 Configuring LLM (Ollama llama3 via LiteLLM proxy)...
🔧 Creating LangChain agent...

📊 Dotazuji incidenty za posledních 7 dní (max 1000 vzorků)...
✅ Data získána z OpenSearch
🔍 Analyzuji data...

📈 Statistiky:
  - Celkový počet incidentů: XXXX
  - Denní průměr: XX.X
  - Kritické incidenty: XX
  - Nejpostiženější region: XXXX

🧠 Generuji analýzu a doporučení pomocí LLM...
✅ Analýza dokončena

📄 Generuji PDF report...
✅ Report vygenerován: reports/wazuh_report_20251128_143022.pdf

✅ HOTOVO! Report byl uložen do: reports/wazuh_report_20251128_143022.pdf
```

## Běžné problémy

### "Connection refused" k MCP serveru
→ MCP server neběží. Spusť v terminálu 1.

### "Connection refused" k LiteLLM
→ Docker container neběží:
```bash
docker-compose up -d
```

### "AuthenticationException" od OpenSearch
→ Zkontroluj credentials v `mcp_server/.env`

### "Model llama3 not found"
→ Pull model:
```bash
ollama pull llama3
```

## Další kroky

- Přečti [README_SETUP.md](README_SETUP.md) pro detaily
- Uprav konfiguraci v `.env` souborech
- Customizuj logo (logo-full-color-cropped.png)
- Nastav `MAX_INCIDENTS_SAMPLE` podle potřeby

## Architektura

```
Terminal 1              Terminal 2           Docker
┌──────────────┐       ┌──────────────┐    ┌──────────────┐
│ MCP Server   │◄──────│ LangChain    │◄───│  LiteLLM     │
│ :8002        │       │ Agent        │    │  :4000       │
└──────┬───────┘       └──────┬───────┘    └──────┬───────┘
       │                      │                   │
       ▼                      ▼                   ▼
┌──────────────┐       ┌──────────────┐    ┌──────────────┐
│ OpenSearch   │       │ PDF Report   │    │ Ollama       │
│ (Wazuh data) │       │              │    │ llama3       │
└──────────────┘       └──────────────┘    └──────────────┘
```

## Příklad reportu

Report obsahuje:
- 📊 Souhrnnou tabulku statistik
- 📈 Časovou osu incidentů (7 dní)
- 🎨 Distribuci podle závažnosti (barevně)
- 🌍 Top 10 regionů (pie chart)
- 🖥️ Top 10 serverů
- 🔧 Top 10 dekoderů
- 💡 Strategická doporučení (AI)
- ⚙️ Taktická/technická doporučení (AI)

Vše v češtině! 🇨🇿
