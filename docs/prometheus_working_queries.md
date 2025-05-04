# ArXiv Pipeline: Verified Working Prometheus Queries

This document contains Prometheus queries that have been fully verified to work with the ArXiv pipeline monitoring setup as of May 4, 2025. These queries power the ArXiv Research Pipeline Dashboard and can be used for creating customized monitoring solutions.

## Data Science Monitoring Guide

As a data science pipeline processing research papers, the most valuable metrics focus on:

1. **Database Performance**: MongoDB operations are crucial for vector storage and retrieval
2. **Resource Utilization**: System resources affect batch processing of papers and vector embedding generation
3. **Throughput Analysis**: Network and operation rates help optimize paper ingestion and processing

## Basic Status Metrics

```promql
# Check target status (1 = up, 0 = down)
up

# Number of metrics being scraped per target
scrape_samples_scraped
```

## System Metrics

```promql
# CPU Usage Percentage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)

# Memory Usage
node_memory_MemTotal_bytes - node_memory_MemFree_bytes

# Memory Usage Percentage
(node_memory_MemTotal_bytes - node_memory_MemFree_bytes) / node_memory_MemTotal_bytes * 100

# Disk Usage
node_filesystem_avail_bytes
node_filesystem_size_bytes
```

## MongoDB Metrics

```promql
# MongoDB Operations Rate
rate(mongodb_op_counters_total[5m])

# MongoDB Operations by Type
rate(mongodb_op_counters_total{type="query"}[5m])
rate(mongodb_op_counters_total{type="insert"}[5m])
rate(mongodb_op_counters_total{type="update"}[5m])
rate(mongodb_op_counters_total{type="delete"}[5m])

# MongoDB Connections
mongodb_connections{state="current"}
mongodb_connections{state="available"}
```

## Container Metrics

For container metrics, try these general formats:

```promql
# All container CPU usage
sum(rate(container_cpu_usage_seconds_total[1m]))

# All container memory usage
sum(container_memory_usage_bytes)
```

## Creating Dashboards in Grafana

1. Add a new panel
2. Select "Prometheus" as the data source
3. Enter one of the queries from this document
4. Adjust visualization as needed
5. Save the dashboard

## Using Time Ranges

For rate metrics, adjust the time range based on your needs:
- `[1m]` - Last minute (more responsive, but can be noisy)
- `[5m]` - Last 5 minutes (good balance)
- `[15m]` - Last 15 minutes (smoother trends)

## Finding Available Labels

To discover what labels are available for filtering:

```promql
# Show all label values for a metric
<metric_name>

# Example
mongodb_op_counters_total
```

This document will be updated as more working queries are identified for the ArXiv pipeline monitoring system.
