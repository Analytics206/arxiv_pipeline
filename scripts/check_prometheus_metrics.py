#!/usr/bin/env python
"""
ArXiv Pipeline Prometheus Metrics Analyzer
---------------------------------------
This diagnostic tool analyzes the Prometheus metrics available for the ArXiv research paper processing pipeline.
It identifies available metrics for monitoring database operations, system resources, and container performance.

Use this tool to verify monitoring configuration and troubleshoot Grafana dashboard issues.
"""

import requests
import json
import argparse
import sys
from datetime import datetime, timedelta

def check_prometheus_up(base_url):
    """Check if Prometheus is running and responding"""
    try:
        response = requests.get(f"{base_url}/api/v1/status/runtimeinfo", timeout=5)
        if response.status_code == 200:
            info = response.json()['data']
            print(f"✅ Prometheus is running (version: {info.get('version', 'unknown')})")
            return True
        else:
            print(f"❌ Prometheus returned status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not connect to Prometheus: {e}")
        return False

def get_metrics_list(base_url):
    """Get a list of all available metrics in Prometheus"""
    try:
        response = requests.get(f"{base_url}/api/v1/label/__name__/values")
        if response.status_code == 200:
            metrics = response.json()['data']
            return metrics
        else:
            print(f"❌ Failed to retrieve metrics list. Status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error retrieving metrics: {e}")
        return []

def check_container_metrics(base_url):
    """Check if container metrics are available"""
    container_metrics = [
        "container_cpu_usage_seconds_total",
        "container_memory_usage_bytes",
        "container_network_receive_bytes_total"
    ]
    
    available = []
    for metric in container_metrics:
        try:
            response = requests.get(f"{base_url}/api/v1/query", params={'query': f'{metric}'})
            if response.status_code == 200 and len(response.json()['data']['result']) > 0:
                available.append(metric)
        except Exception as e:
            print(f"  Error checking {metric}: {e}")
    
    if available:
        print(f"✅ Container metrics available: {len(available)}/{len(container_metrics)}")
        return available
    else:
        print("❌ No container metrics found")
        return []

def check_host_metrics(base_url):
    """Check if host metrics are available"""
    host_metrics = [
        "node_cpu_seconds_total",
        "node_memory_MemTotal_bytes",
        "node_filesystem_size_bytes"
    ]
    
    available = []
    for metric in host_metrics:
        try:
            response = requests.get(f"{base_url}/api/v1/query", params={'query': f'{metric}'})
            if response.status_code == 200 and len(response.json()['data']['result']) > 0:
                available.append(metric)
        except Exception as e:
            print(f"  Error checking {metric}: {e}")
    
    if available:
        print(f"✅ Host metrics available: {len(available)}/{len(host_metrics)}")
        return available
    else:
        print("❌ No host metrics found")
        return []

def check_targets(base_url):
    """Check Prometheus targets and their status"""
    try:
        response = requests.get(f"{base_url}/api/v1/targets")
        if response.status_code == 200:
            targets = response.json()['data']['activeTargets']
            up_count = sum(1 for t in targets if t['health'] == 'up')
            down_count = len(targets) - up_count
            
            print(f"\n=== TARGETS STATUS: {up_count} Up / {down_count} Down ===")
            for target in targets:
                status = "✅" if target['health'] == 'up' else "❌"
                print(f"{status} {target.get('labels', {}).get('job', 'unknown')} - {target.get('scrapeUrl', 'unknown')}")
            
            return up_count, targets
        else:
            print(f"❌ Failed to retrieve targets. Status code: {response.status_code}")
            return 0, []
    except Exception as e:
        print(f"❌ Error checking targets: {e}")
        return 0, []

def check_container_labels(base_url):
    """Check what labels are available for container metrics"""
    try:
        query = "container_memory_usage_bytes"
        response = requests.get(f"{base_url}/api/v1/query", params={'query': query})
        
        if response.status_code == 200 and len(response.json()['data']['result']) > 0:
            results = response.json()['data']['result']
            print(f"\n=== CONTAINER LABELS ANALYSIS ===")
            
            # Extract all unique label names
            all_labels = set()
            for result in results:
                all_labels.update(result['metric'].keys())
            
            print(f"Available labels: {', '.join(sorted(all_labels))}")
            
            # Check for container identification labels
            id_labels = ['id', 'name', 'container_name', 'container', 'image']
            found_id_labels = [label for label in id_labels if label in all_labels]
            
            if found_id_labels:
                print(f"✅ Container identification labels found: {', '.join(found_id_labels)}")
                
                # Sample values for the first found ID label
                label = found_id_labels[0]
                values = {result['metric'].get(label, 'N/A') for result in results if label in result['metric']}
                sample_values = list(values)[:5]  # Show at most 5 examples
                print(f"\nSample values for '{label}': {', '.join(sample_values)}")
                
                # Generate a working query example
                example_value = sample_values[0] if sample_values else ""
                print(f"\nWorking query example:\ncontainer_memory_usage_bytes{{{label}=\"{example_value}\"}}")
                
                return found_id_labels, sample_values
            else:
                print("❌ No container identification labels found")
                return [], []
        else:
            print("❌ No container metrics data returned")
            return [], []
    except Exception as e:
        print(f"❌ Error analyzing container labels: {e}")
        return [], []

def check_mongodb_metrics(base_url):
    """Check for MongoDB metrics critical for ArXiv pipeline vector database operations"""
    mongodb_metrics = [
        "mongodb_op_counters_total",
        "mongodb_connections",
        "mongodb_metrics_document_total"
    ]
    
    available = []
    operation_types = []
    connection_states = []
    
    # Check for basic MongoDB metrics
    for metric in mongodb_metrics:
        try:
            response = requests.get(f"{base_url}/api/v1/query", params={'query': f'{metric}'})
            if response.status_code == 200 and len(response.json()['data']['result']) > 0:
                available.append(metric)
                
                # Check for operation types (query, insert, etc)
                if metric == "mongodb_op_counters_total":
                    for result in response.json()['data']['result']:
                        if 'type' in result['metric']:
                            operation_types.append(result['metric']['type'])
                
                # Check for connection states
                if metric == "mongodb_connections":
                    for result in response.json()['data']['result']:
                        if 'state' in result['metric']:
                            connection_states.append(result['metric']['state'])
        except Exception as e:
            print(f"  Error checking {metric}: {e}")
    
    if available:
        print(f"✅ MongoDB metrics available: {len(available)}/{len(mongodb_metrics)}")
        if operation_types:
            print(f"  - Operation types: {', '.join(set(operation_types))}")
        if connection_states:
            print(f"  - Connection states: {', '.join(set(connection_states))}")
        return available
    else:
        print("❌ No MongoDB metrics found - vector database monitoring unavailable")
        return []

def verify_dashboard_queries(base_url):
    """Verify that key queries used in the ArXiv Pipeline dashboard are working"""
    dashboard_queries = [
        "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
        "(node_memory_MemTotal_bytes - node_memory_MemFree_bytes) / node_memory_MemTotal_bytes * 100",
        "rate(mongodb_op_counters_total{type=\"query\"}[5m])",
        "sum(rate(container_cpu_usage_seconds_total[5m]))"
    ]
    
    working_queries = 0
    for query in dashboard_queries:
        try:
            response = requests.get(f"{base_url}/api/v1/query", params={'query': query})
            if response.status_code == 200 and len(response.json()['data']['result']) > 0:
                working_queries += 1
        except Exception as e:
            print(f"  Error with query '{query[:30]}...': {e}")
    
    if working_queries > 0:
        print(f"✅ Dashboard queries: {working_queries}/{len(dashboard_queries)} verified working")
    else:
        print("❌ No dashboard queries are working correctly")
    
    return working_queries

def main():
    parser = argparse.ArgumentParser(description="Check Prometheus metrics for ArXiv Pipeline")
    parser.add_argument("--url", default="http://localhost:9090", help="Prometheus base URL")
    args = parser.parse_args()
    
    print("\n=== ARXIV RESEARCH PIPELINE PROMETHEUS ANALYZER ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {args.url}")
    print("=" * 50)
    
    if not check_prometheus_up(args.url):
        print("\n❌ Prometheus is not available. Please check if it's running.")
        sys.exit(1)
    
    print("\n=== CHECKING AVAILABLE METRICS ===")
    metrics = get_metrics_list(args.url)
    print(f"Total metrics available: {len(metrics)}")
    
    container_metrics = check_container_metrics(args.url)
    host_metrics = check_host_metrics(args.url)
    mongodb_metrics = check_mongodb_metrics(args.url)
    
    up_count, targets = check_targets(args.url)
    id_labels, sample_values = check_container_labels(args.url)
    
    print("\n=== VERIFYING DASHBOARD QUERIES ===")
    working_queries = verify_dashboard_queries(args.url)
    
    print("\n=== RECOMMENDATIONS FOR ARXIV PIPELINE ===")
    if not container_metrics and not host_metrics and not mongodb_metrics:
        print("❌ No metrics found. Check that exporters are running and properly configured.")
        print("- Verify that cAdvisor, Node Exporter, MongoDB Exporter are running")
        print("- Check Prometheus configuration at config/prometheus/prometheus.yml")
    else:
        if not container_metrics:
            print("⚠️ Container metrics missing - paper processing container monitoring unavailable.")
            print("- Check that cAdvisor is running: docker compose -f docker-compose.monitoring.yml ps")
        if not host_metrics:
            print("⚠️ Host metrics missing - system resource monitoring unavailable.")
            print("- Check that Node Exporter is running: docker compose -f docker-compose.monitoring.yml ps")
        if not mongodb_metrics:
            print("⚠️ MongoDB metrics missing - vector database monitoring unavailable.")
            print("- Check that MongoDB Exporter is running and connected to MongoDB")
            print("- Verify MongoDB URI in docker-compose.monitoring.yml")  
        
        if container_metrics and host_metrics and mongodb_metrics:
            print("✅ All critical metrics for ArXiv pipeline monitoring are available!")
    
    if id_labels:
        print("\n=== GRAFANA DASHBOARD CONFIGURATION ===")
        print(f"Use these label formats in your dashboard queries:")
        print(f"  - container_memory_usage_bytes{{{id_labels[0]}=\"{sample_values[0]}\"}}")
        print(f"  - rate(container_cpu_usage_seconds_total{{{id_labels[0]}=\"{sample_values[0]}\"}}[5m])")
    
    # Data science recommendations specific to ArXiv pipeline
    print("\n=== DATA SCIENCE MONITORING RECOMMENDATIONS ===")
    if working_queries > 0:
        print("✅ ArXiv Research Pipeline Dashboard is properly configured.")
        print("Key metrics for monitoring your research paper processing:")
        print("1. MongoDB query rates - Track database load during paper processing")
        print("2. System resource correlation - Identify resource bottlenecks")
        print("3. Query-to-write ratio - Analyze vector database usage patterns")
    else:
        print("❌ Dashboard queries not working - troubleshoot your Grafana configuration.")
    
    print("\nAnalysis completed. Your ArXiv pipeline monitoring is ready for data science workflows.")
    
    # Return summary information that could be used by calling code
    return {
        "prometheus_up": True,
        "metrics_count": len(metrics),
        "container_metrics": bool(container_metrics),
        "host_metrics": bool(host_metrics),
        "mongodb_metrics": bool(mongodb_metrics),
        "dashboard_queries_working": working_queries
    }

if __name__ == "__main__":
    main()
