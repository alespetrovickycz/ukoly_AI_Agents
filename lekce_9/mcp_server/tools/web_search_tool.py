import json
from datetime import datetime
from typing import Optional
import asyncio
from ddgs import DDGS


async def web_search(
    query: str,
    max_results: int = 5,
    region: str = "wt-wt"
) -> str:
    """
    Search the web for information using DuckDuckGo.

    Args:
        query: Search query string
        max_results: Number of results to return (1-20, default: 5)
        region: Region code for search (default: "wt-wt" for worldwide)
                Examples: "us-en" (USA), "uk-en" (UK), "cs-cz" (Czech), "wt-wt" (worldwide)

    Returns:
        JSON string with search results including titles, URLs, and snippets
    """
    try:
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        query = query.strip()

        # Validate max_results range
        if max_results < 1 or max_results > 20:
            raise ValueError("max_results must be between 1 and 20")

        # Perform search using DDGS in executor to avoid blocking
        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(
                    query=query,
                    region=region,
                    max_results=max_results
                ))

        loop = asyncio.get_event_loop()
        search_results = await loop.run_in_executor(None, _search)

        # Format results
        formatted_results = []
        for idx, result in enumerate(search_results, start=1):
            formatted_results.append({
                "position": idx,
                "title": result.get("title", ""),
                "url": result.get("href", ""),
                "snippet": result.get("body", "")
            })

        # Prepare response
        response = {
            "query_info": {
                "query": query,
                "max_results": max_results,
                "region": region,
                "timestamp": datetime.now().isoformat()
            },
            "total_results": len(formatted_results),
            "results": formatted_results
        }

        return json.dumps(response, indent=2, ensure_ascii=False)

    except Exception as e:
        error_result = {
            "error": str(e),
            "query_info": {
                "query": query,
                "max_results": max_results,
                "region": region
            }
        }
        return json.dumps(error_result, indent=2)
