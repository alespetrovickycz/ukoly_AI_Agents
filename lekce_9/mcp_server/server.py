import asyncio
import logging
import os
from typing import Any, Dict, Optional
import contextlib
from collections.abc import AsyncIterator
import uvicorn

# MCP
from mcp.server.lowlevel import Server
import mcp.types as types

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

# Import tool implementation
from tools.opensearch_tool import search_wazuh_incidents
from tools.web_search_tool import web_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("wazuh-mcp-server")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available tools with their schemas."""
    return [
        types.Tool(
            name="search_wazuh_incidents",
            description="Search Wazuh security incidents from OpenSearch for the last N days with aggregated statistics. Returns incident data, aggregations by severity level, region, incident type (groups), server (agent), and decoder, plus timeline data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "anyOf": [
                            {"type": "integer"},
                            {"type": "string", "pattern": "^[0-9]+$"}
                        ],
                        "description": "Number of days to query (default: 7)",
                        "default": 7,
                    },
                    "max_sample_size": {
                        "anyOf": [
                            {"type": "integer"},
                            {"type": "string", "pattern": "^[0-9]+$"}
                        ],
                        "description": "Maximum number of sample incidents for detailed analysis (default: 1000)",
                        "default": 1000,
                    },
                    "query_type": {
                        "type": "string",
                        "description": "Type of query: 'all' (with aggregations), 'sample' (just documents)",
                        "enum": ["all", "sample"],
                        "default": "all",
                    },
                },
            },
        ),
        types.Tool(
            name="web_search",
            description="Search the web for information using DuckDuckGo. Returns search results with titles, URLs, and snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "max_results": {
                        "anyOf": [
                            {"type": "integer"},
                            {"type": "string", "pattern": "^[0-9]+$"}
                        ],
                        "description": "Number of results to return (1-20, default: 5)",
                        "default": 5
                    },
                    "region": {
                        "type": "string",
                        "description": "Region code for search (e.g., 'us-en', 'uk-en', 'wt-wt' for worldwide)",
                        "default": "wt-wt"
                    }
                },
                "required": ["query"]
            }
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Optional[Dict[str, Any]] = None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    if arguments is None:
        arguments = {}

    try:
        if name == "search_wazuh_incidents":
            # Convert string parameters to correct types (LLM sometimes sends strings)
            days = arguments.get("days", 7)
            max_sample_size = arguments.get("max_sample_size", 1000)

            # Ensure integers
            if isinstance(days, str):
                days = int(days)
            if isinstance(max_sample_size, str):
                max_sample_size = int(max_sample_size)

            result = await search_wazuh_incidents(
                days=days,
                max_sample_size=max_sample_size,
                query_type=arguments.get("query_type", "all"),
            )
            return [types.TextContent(type="text", text=result)]

        elif name == "web_search":
            # Extract and validate parameters
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 5)
            region = arguments.get("region", "wt-wt")

            # Convert string to int if needed
            if isinstance(max_results, str):
                max_results = int(max_results)

            # Call the tool
            result = await web_search(
                query=query,
                max_results=max_results,
                region=region
            )
            return [types.TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Tool execution error: {str(e)}"
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]


# ---------------------------------
# StreamableHTTP Server Transport
# ---------------------------------

# Create the session manager
session_manager = StreamableHTTPSessionManager(
    app=server,
    json_response=True,  # Use JSON responses
    event_store=None,  # No resumability
    stateless=True,
)


# ASGI handler for streamable HTTP connections
async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    """Context manager for managing session manager lifecycle."""
    async with session_manager.run():
        logger.info("Wazuh MCP Server started with StreamableHTTP session manager!")
        logger.info("Server listening on http://0.0.0.0:8002/mcp")
        try:
            yield
        finally:
            logger.info("Wazuh MCP Server shutting down...")


starlette_app = Starlette(
    debug=True,
    routes=[
        Mount("/mcp", app=handle_streamable_http),
    ],
    lifespan=lifespan,
)

if __name__ == "__main__":
    try:
        logger.info("Starting Wazuh MCP server...")
        # Run the server
        uvicorn.run(starlette_app, host="0.0.0.0", port=8002)
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        raise e
