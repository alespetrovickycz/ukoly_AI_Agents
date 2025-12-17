"""LangChain agent for Wazuh incident analysis."""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

from analyzer import (
    extract_incident_data_from_mcp_response,
    format_data_for_llm_analysis
)
from pdf_generator import generate_pdf_report

# Load environment variables
load_dotenv()


async def get_mcp_tools():
    """Load tools from Wazuh MCP server."""
    mcp_url = os.getenv("WAZUH_MCP_URL", "http://localhost:8002/mcp")

    client = MultiServerMCPClient({
        "wazuh": {
            "transport": "streamable_http",
            "url": mcp_url,
        }
    })

    tools = await client.get_tools()
    return tools, client


async def main():
    """Main agent workflow."""
    print("🚀 Starting Wazuh Incident Analysis Agent...")

    # Configuration
    max_sample_size = int(os.getenv("MAX_INCIDENTS_SAMPLE", "1000"))
    report_output_dir = os.getenv("REPORT_OUTPUT_DIR", "./reports")
    logo_path = os.getenv("COMPANY_LOGO_PATH", "./logo-full-color-cropped.png")

    # Ensure output directory exists
    os.makedirs(report_output_dir, exist_ok=True)

    # 1. Connect to MCP server and load tools
    print("📡 Connecting to Wazuh MCP server...")
    mcp_tools, mcp_client = await get_mcp_tools()
    print(f"✅ Loaded {len(mcp_tools)} tools from MCP server")

    # 2. Configure LLM (Ollama via LiteLLM proxy)
    print("🤖 Configuring LLM (Ollama llama3 via LiteLLM proxy)...")
    litellm_base_url = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
    litellm_api_key = os.getenv("LITELLM_API_KEY", "dummy-key")

    llm = ChatOpenAI(
        base_url=litellm_base_url,
        api_key=litellm_api_key,
        #model="ollama-llama3.1",
        #model="gpt-5-nano",
        #model="gpt-4.1",
        model="gemini-2.5-pro",
        temperature=0.7
    )

    # 3. Create LangChain agent
    print("🔧 Creating LangChain agent...")
    agent = create_agent(
        llm,
        tools=mcp_tools,
        system_prompt="""Jsi expert na kybernetickou bezpečnost a analýzu bezpečnostních incidentů.
Analyzuj Wazuh bezpečnostní incidenty a identifikuj vzory, trendy a anomálie.
Poskytuj doporučení jak strategická (high-level směřování), tak taktická (konkrétní technická opatření)
pro snížení počtu incidentů.
Zaměř se na: úrovně závažnosti, geografické vzory, typy útoků, postižené servery.

DOSTUPNÉ TOOLS:
- search_wazuh_incidents: Vyhledá Wazuh incidenty z OpenSearch. Parametry: days (int), max_sample_size (int), query_type (string).

Používej POUZE tyto dostupné tools. NEVYMÝŠLEJ SI názvy tools.
Všechny odpovědi a doporučení piš v češtině."""
    )

    # 4. Query incidents - call MCP tool directly to ensure correct parameters
    print(f"\n📊 Dotazuji incidenty za posledních 7 dní (max {max_sample_size} vzorků)...")

    try:
        # Call the MCP tool directly with exact parameters
        search_tool = None
        for tool in mcp_tools:
            if hasattr(tool, 'name') and 'search_wazuh_incidents' in tool.name:
                search_tool = tool
                break

        if not search_tool:
            print("❌ Tool search_wazuh_incidents not found!")
            return

        # Invoke the tool directly with correct parameters
        mcp_response_text = await search_tool.ainvoke({
            "days": 7,
            "max_sample_size": max_sample_size,
            "query_type": "all"
        })

        print("✅ Data získána z OpenSearch")

        # Parse incident data
        print("🔍 Analyzuji data...")
        incident_data = extract_incident_data_from_mcp_response(mcp_response_text)

        print(f"\n📈 Statistiky:")
        print(f"  - Celkový počet incidentů: {incident_data['statistics']['total_incidents']}")
        print(f"  - Denní průměr: {incident_data['statistics']['daily_average']}")
        print(f"  - Kritické incidenty: {incident_data['statistics']['critical_count']}")
        print(f"  - Země - největší zdroj incidentů: {incident_data['statistics']['top_country']}")

        # 5. Generate LLM analysis and recommendations
        print("\n🧠 Generuji analýzu a doporučení pomocí LLM...")

        formatted_data = format_data_for_llm_analysis(incident_data)

        # Call LLM directly without agent to avoid tool-calling behavior
        analysis_prompt = f"""Jsi expert na kybernetickou bezpečnost.

Na základě těchto Wazuh incidentů napiš analýzu a doporučení v PROSTÉM TEXTU (ne JSON).

{formatted_data}

Napiš odpověď ve formátu:

STRUČNÁ ANALÝZA WAZUH INCIDENTŮ

[2-3 odstavce sumarizující bezpečnostní situaci]

STRATEGICKÁ DOPORUČENÍ

1. [První strategické doporučení]
2. [Druhé strategické doporučení]
3. [Třetí strategické doporučení]
4. [Čtvrté strategické doporučení]
5. [Páté strategické doporučení]

TAKTICKÁ A TECHNICKÁ DOPORUČENÍ

1. [První taktické doporučení - konkrétní IP adresy a servery]
2. [Druhé taktické doporučení]
3. [Třetí taktické doporučení]
4. [Čtvrté taktické doporučení]
5. [Páté taktické doporučení]

Používej konkrétní data - IP adresy, názvy serverů, čísla z analýzy.
"""

        # Call LLM directly without agent framework
        from langchain_core.messages import HumanMessage

        llm_response = await llm.ainvoke([HumanMessage(content=analysis_prompt)])

        # Extract text from response
        if hasattr(llm_response, 'content'):
            analysis_text = llm_response.content
        else:
            analysis_text = str(llm_response)

        # Clean up if needed
        if not analysis_text or len(analysis_text) < 100:
            analysis_text = "Nepodařilo se vygenerovat analýzu. LLM vrátilo prázdnou nebo příliš krátkou odpověď."

        print("✅ Analýza dokončena")

        # 6. Generate PDF report
        print("\n📄 Generuji PDF report...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(report_output_dir, f"wazuh_report_{timestamp}.pdf")

        generate_pdf_report(
            incident_data=incident_data,
            analysis=analysis_text,
            output_file=output_file,
            logo_path=logo_path
        )

        print(f"\n✅ HOTOVO! Report byl uložen do: {output_file}")

    except Exception as e:
        print(f"\n❌ Chyba během zpracování: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup (MultiServerMCPClient doesn't have cleanup method)
        pass


if __name__ == "__main__":
    asyncio.run(main())
