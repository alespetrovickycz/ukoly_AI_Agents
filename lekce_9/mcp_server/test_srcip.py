import os
from dotenv import load_dotenv
from opensearchpy import OpenSearch

load_dotenv()

host = os.getenv('OPENSEARCH_HOST', 'localhost').replace('https://', '').replace('http://', '')
port = int(os.getenv('OPENSEARCH_PORT', '9200'))
username = os.getenv('OPENSEARCH_USERNAME', 'admin')
password = os.getenv('OPENSEARCH_PASSWORD', 'admin')

client = OpenSearch(
    hosts=[{'host': host, 'port': port}],
    http_auth=(username, password),
    use_ssl=True,
    verify_certs=False,
    ssl_show_warn=False
)

# Query to check srcip field
query = {
    "size": 10,
    "query": {"match_all": {}},
    "_source": ["data.srcip", "data", "timestamp"],
    "sort": [{"timestamp": "desc"}]
}

response = client.search(index="wazuh-alerts-4.x-2025.11.28", body=query)

print("Checking data.srcip field in recent incidents:")
print("=" * 80)
for i, hit in enumerate(response["hits"]["hits"][:10], 1):
    data = hit["_source"].get("data", {})
    srcip = data.get("srcip") if data else None
    print(f"{i}. srcip: {srcip}")
    print(f"   Full data keys: {list(data.keys()) if data else 'None'}")
    print()

# Check aggregation
agg_query = {
    "size": 0,
    "aggs": {
        "by_srcip": {
            "terms": {"field": "data.srcip", "size": 20, "missing": "N/A"}
        }
    }
}

agg_response = client.search(index="wazuh-alerts-4.x-*", body=agg_query)
print("\nAggregation results for data.srcip:")
print("=" * 80)
for bucket in agg_response["aggregations"]["by_srcip"]["buckets"][:10]:
    print(f"  {bucket['key']}: {bucket['doc_count']} incidents")
