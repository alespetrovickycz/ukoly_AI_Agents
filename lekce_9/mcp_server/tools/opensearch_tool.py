import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from opensearchpy import OpenSearch
from dotenv import load_dotenv

load_dotenv()


def generate_index_pattern(days: int = 7) -> str:
    """Generate comma-separated indices for last N days.

    Example: wazuh-alerts-4.x-2025.11.28,wazuh-alerts-4.x-2025.11.29,...
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days-1)

    indices = []
    current = start_date
    while current <= end_date:
        index_name = f"wazuh-alerts-4.x-{current.strftime('%Y.%m.%d')}"
        indices.append(index_name)
        current += timedelta(days=1)

    return ','.join(indices)


def get_opensearch_client() -> OpenSearch:
    """Create and return OpenSearch client with configuration from environment."""
    host = os.getenv('OPENSEARCH_HOST', 'localhost')
    port = int(os.getenv('OPENSEARCH_PORT', '9200'))
    username = os.getenv('OPENSEARCH_USERNAME', 'admin')
    password = os.getenv('OPENSEARCH_PASSWORD', 'admin')
    use_ssl = os.getenv('OPENSEARCH_USE_SSL', 'false').lower() == 'true'
    verify_certs = os.getenv('OPENSEARCH_VERIFY_CERTS', 'false').lower() == 'true'

    # Strip protocol from host if present
    host = host.replace('https://', '').replace('http://', '')

    config = {
        "hosts": [{'host': host, 'port': port}],
        "http_auth": (username, password),
        "use_ssl": use_ssl,
        "verify_certs": verify_certs,
        "ssl_show_warn": False
    }

    return OpenSearch(**config)


async def search_wazuh_incidents(
    days: int = 7,
    max_sample_size: int = 1000,
    query_type: str = "all"
) -> str:
    """
    Search Wazuh security incidents from OpenSearch for the last N days.

    Args:
        days: Number of days to query (default: 7)
        max_sample_size: Maximum number of sample incidents for detailed analysis (default: 1000)
        query_type: Type of query - 'all' (with aggregations) or 'sample' (just documents)

    Returns:
        JSON string with incident data and aggregations
    """
    try:
        # Generate index pattern for the date range
        index_pattern = generate_index_pattern(days)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days-1)
        start_date_str = start_date.strftime('%Y-%m-%dT00:00:00')
        end_date_str = end_date.strftime('%Y-%m-%dT23:59:59')

        # Build query
        query_body = {
            "track_total_hits": True,  # Get accurate total count (not limited to 10000)
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "timestamp": {
                                    "gte": start_date_str,
                                    "lte": end_date_str
                                }
                            }
                        }
                    ]
                }
            },
            "size": max_sample_size if query_type == "all" else 0,
            "sort": [{"timestamp": {"order": "desc"}}]
        }

        # Add aggregations for 'all' query type
        if query_type == "all":
            query_body["aggs"] = {
                "by_level": {
                    "terms": {"field": "rule.level", "size": 20}
                },
                "by_region": {
                    "terms": {"field": "GeoLocation.country_name", "size": 20, "missing": "N/A"}
                },
                "by_groups": {
                    "terms": {"field": "rule.groups", "size": 20}
                },
                "by_agent": {
                    "terms": {"field": "agent.name", "size": 20}
                },
                "by_decoder": {
                    "terms": {"field": "decoder.name", "size": 20}
                },
                "by_srcip": {
                    "terms": {"field": "data.srcip", "size": 20, "missing": "N/A"}
                },
                "timeline": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "day",
                        "format": "yyyy-MM-dd"
                    }
                }
            }

        # Execute query
        client = get_opensearch_client()
        response = client.search(index=index_pattern, body=query_body)

        # Prepare result
        result = {
            "query_info": {
                "start_date": start_date_str,
                "end_date": end_date_str,
                "days": days,
                "index_pattern": index_pattern,
                "max_sample_size": max_sample_size
            },
            "total_hits": response["hits"]["total"]["value"],
            "sample_incidents": []
        }

        # Add sample incidents
        for hit in response["hits"]["hits"]:
            incident = {
                "timestamp": hit["_source"].get("timestamp"),
                "agent_name": hit["_source"].get("agent", {}).get("name"),
                "agent_ip": hit["_source"].get("agent", {}).get("ip"),
                "rule_level": hit["_source"].get("rule", {}).get("level"),
                "rule_description": hit["_source"].get("rule", {}).get("description"),
                "rule_groups": hit["_source"].get("rule", {}).get("groups", []),
                "decoder_name": hit["_source"].get("decoder", {}).get("name"),
                "region_name": hit["_source"].get("GeoLocation", {}).get("region_name"),
                "country_name": hit["_source"].get("GeoLocation", {}).get("country_name"),
                "src_ip": hit["_source"].get("data", {}).get("srcip"),
                "url": hit["_source"].get("data", {}).get("url"),
                "full_log": hit["_source"].get("full_log", "")[:500]  # Truncate for readability
            }
            result["sample_incidents"].append(incident)

        # Add aggregations
        if "aggregations" in response:
            result["aggregations"] = {
                "by_level": {
                    "buckets": response["aggregations"]["by_level"]["buckets"]
                },
                "by_region": {
                    "buckets": response["aggregations"]["by_region"]["buckets"]
                },
                "by_groups": {
                    "buckets": response["aggregations"]["by_groups"]["buckets"]
                },
                "by_agent": {
                    "buckets": response["aggregations"]["by_agent"]["buckets"]
                },
                "by_decoder": {
                    "buckets": response["aggregations"]["by_decoder"]["buckets"]
                },
                "by_srcip": {
                    "buckets": response["aggregations"]["by_srcip"]["buckets"]
                },
                "timeline": {
                    "buckets": response["aggregations"]["timeline"]["buckets"]
                }
            }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        error_result = {
            "error": str(e),
            "query_info": {
                "days": days,
                "max_sample_size": max_sample_size,
                "query_type": query_type
            }
        }
        return json.dumps(error_result, indent=2)
