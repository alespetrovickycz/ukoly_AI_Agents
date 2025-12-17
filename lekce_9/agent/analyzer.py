"""Data analyzer for Wazuh incident data."""
import json
from typing import Dict, Any, List
import pandas as pd


def parse_bucket_aggregation(bucket_data: List[Dict]) -> Dict[Any, int]:
    """Parse OpenSearch bucket aggregation into a dictionary.

    Args:
        bucket_data: List of buckets with 'key' and 'doc_count'

    Returns:
        Dictionary mapping keys to counts (keys can be str or int)
    """
    # Keep keys as-is from OpenSearch (integers for severity, strings for others)
    return {bucket["key"]: bucket["doc_count"] for bucket in bucket_data}


def parse_timeline_aggregation(timeline_data: List[Dict]) -> pd.DataFrame:
    """Parse timeline aggregation into pandas DataFrame.

    Args:
        timeline_data: List of timeline buckets

    Returns:
        DataFrame with 'date' and 'count' columns
    """
    data = []
    for bucket in timeline_data:
        data.append({
            "date": bucket["key_as_string"],
            "count": bucket["doc_count"]
        })

    return pd.DataFrame(data)


def parse_aggregations(agg_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse all OpenSearch aggregations into chart-ready format.

    Args:
        agg_data: Aggregations dictionary from OpenSearch response

    Returns:
        Dictionary with parsed aggregations
    """
    return {
        "severity": parse_bucket_aggregation(agg_data.get("by_level", {}).get("buckets", [])),
        "regions": parse_bucket_aggregation(agg_data.get("by_region", {}).get("buckets", [])),
        "types": parse_bucket_aggregation(agg_data.get("by_groups", {}).get("buckets", [])),
        "agents": parse_bucket_aggregation(agg_data.get("by_agent", {}).get("buckets", [])),
        "decoders": parse_bucket_aggregation(agg_data.get("by_decoder", {}).get("buckets", [])),
        "srcips": parse_bucket_aggregation(agg_data.get("by_srcip", {}).get("buckets", [])),
        "timeline": parse_timeline_aggregation(agg_data.get("timeline", {}).get("buckets", []))
    }


def calculate_statistics(total_hits: int, parsed_data: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
    """Calculate summary statistics from parsed data.

    Args:
        total_hits: Total number of incidents
        parsed_data: Dictionary with parsed aggregations
        days: Number of days in the report

    Returns:
        Dictionary with calculated statistics
    """
    severity_data = parsed_data["severity"]
    regions_data = parsed_data["regions"]
    types_data = parsed_data["types"]
    srcips_data = parsed_data.get("srcips", {})

    # Calculate critical incidents (level > 9)
    critical_count = sum(count for level, count in severity_data.items() if int(level) > 9)

    # Find top country and incident type (filter out N/A)
    regions_no_na = {k: v for k, v in regions_data.items() if k != "N/A"}
    types_no_na = {k: v for k, v in types_data.items() if k != "N/A"}
    srcips_no_na = {k: v for k, v in srcips_data.items() if k != "N/A"}

    top_country = max(regions_no_na.items(), key=lambda x: x[1])[0] if regions_no_na else "N/A"
    top_incident_type = max(types_no_na.items(), key=lambda x: x[1])[0] if types_no_na else "N/A"
    top_srcip = max(srcips_no_na.items(), key=lambda x: x[1])[0] if srcips_no_na else "N/A"

    return {
        "total_incidents": total_hits,
        "daily_average": round(total_hits / days, 1),
        "critical_count": critical_count,
        "top_country": top_country,
        "top_incident_type": top_incident_type,
        "top_srcip": top_srcip,
        "top_srcip_count": srcips_no_na.get(top_srcip, 0) if top_srcip != "N/A" else 0
    }


def extract_incident_data_from_mcp_response(mcp_response_text: str) -> Dict[str, Any]:
    """Extract and structure incident data from MCP tool response.

    Args:
        mcp_response_text: JSON string returned by MCP tool

    Returns:
        Dictionary with structured incident data
    """
    try:
        raw_data = json.loads(mcp_response_text)

        # Check for errors
        if "error" in raw_data:
            raise ValueError(f"MCP tool error: {raw_data['error']}")

        # Parse aggregations
        aggregations = raw_data.get("aggregations", {})
        parsed_aggs = parse_aggregations(aggregations)

        # Calculate statistics
        total_hits = raw_data.get("total_hits", 0)
        days = raw_data.get("query_info", {}).get("days", 7)
        stats = calculate_statistics(total_hits, parsed_aggs, days)

        # Combine everything
        result = {
            "query_info": raw_data.get("query_info", {}),
            "total_hits": total_hits,
            "statistics": stats,
            "aggregations": parsed_aggs,
            "sample_incidents": raw_data.get("sample_incidents", [])
        }

        return result

    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse MCP response as JSON: {e}")
    except Exception as e:
        raise ValueError(f"Error extracting incident data: {e}")


def format_data_for_llm_analysis(incident_data: Dict[str, Any]) -> str:
    """Format incident data for LLM analysis.

    Args:
        incident_data: Structured incident data

    Returns:
        Formatted string for LLM prompt
    """
    stats = incident_data["statistics"]
    aggs = incident_data["aggregations"]

    # Top items from each category
    top_regions = sorted(aggs["regions"].items(), key=lambda x: x[1], reverse=True)[:10]
    top_types = sorted(aggs["types"].items(), key=lambda x: x[1], reverse=True)[:10]
    top_agents = sorted(aggs["agents"].items(), key=lambda x: x[1], reverse=True)[:10]
    top_decoders = sorted(aggs["decoders"].items(), key=lambda x: x[1], reverse=True)[:10]
    top_srcips = sorted(aggs.get("srcips", {}).items(), key=lambda x: x[1], reverse=True)[:20]

    # Format severity distribution
    severity_dist = "\n".join([f"  - Úroveň {level}: {count} incidentů" for level, count in sorted(aggs["severity"].items())])

    # Format timeline
    timeline_df = aggs["timeline"]
    timeline_str = "\n".join([f"  - {row['date']}: {row['count']} incidentů" for _, row in timeline_df.iterrows()])

    formatted = f"""
PŘEHLED BEZPEČNOSTNÍCH INCIDENTŮ

Základní statistiky:
- Celkový počet incidentů: {stats['total_incidents']}
- Denní průměr: {stats['daily_average']}
- Kritické incidenty (úroveň >9): {stats['critical_count']}
- Země která je největším zdrojem incidentů: {stats['top_country']}
- Nejčastější typ incidentu: {stats['top_incident_type']}
- Nejaktivnější útočící IP: {stats['top_srcip']} ({stats['top_srcip_count']} útoků)

Distribuce podle závažnosti:
{severity_dist}

Časová osa (denní počty):
{timeline_str}

Top 10 zemí podle počtu incidentů:
{chr(10).join([f"  - {region}: {count}" for region, count in top_regions])}

Top 10 typů incidentů:
{chr(10).join([f"  - {itype}: {count}" for itype, count in top_types])}

Top 10 serverů (agentů) s nejvíce incidenty:
{chr(10).join([f"  - {agent}: {count}" for agent, count in top_agents])}

Top 10 dekoderů:
{chr(10).join([f"  - {decoder}: {count}" for decoder, count in top_decoders])}

Top 20 útočících IP adres:
{chr(10).join([f"  - {srcip}: {count} útoků" for srcip, count in top_srcips])}

Vzorky incidentů (prvních 200):
"""
    # Add sample incidents - změna z 5 na 200
    for i, incident in enumerate(incident_data["sample_incidents"][:200], 1):
        formatted += f"""
Incident #{i}:
  - Čas: {incident.get('timestamp', 'N/A')}
  - Server: {incident.get('agent_name', 'N/A')}
  - Závažnost: {incident.get('rule_level', 'N/A')}
  - Popis: {incident.get('rule_description', 'N/A')}
  - Typy: {', '.join(incident.get('rule_groups', []))}
  - Země: {incident.get('country_name', 'N/A')}
  - Zdrojová IP: {incident.get('src_ip', 'N/A')}
  - URL: {incident.get('url', 'N/A')}
  - Log: {incident.get('full_log', 'N/A')[:200]}
"""

    return formatted
