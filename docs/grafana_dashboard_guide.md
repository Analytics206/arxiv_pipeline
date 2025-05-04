# ArXiv Pipeline Monitoring Dashboard Guide

This guide provides instructions for enhancing your Prometheus/Grafana monitoring for the ArXiv Deep Research Pipeline.

## Current Dashboard Status

You now have a working dashboard with verified queries. This provides a foundation to build upon for comprehensive monitoring of your research paper processing pipeline.

## Recommended Dashboard Panels

### 1. System Health Section

These panels monitor the underlying infrastructure supporting your data processing:

```promql
# CPU Usage Panel
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory Usage Panel
(node_memory_MemTotal_bytes - node_memory_MemFree_bytes) / node_memory_MemTotal_bytes * 100

# Disk Space Panel
100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes)
```

### 2. MongoDB Analytics Section

These panels help monitor database performance during paper processing and vector operations:

```promql
# Query Operations Panel (Bar Gauge)
rate(mongodb_op_counters_total{type="query"}[5m])

# Write Operations Panel (Time Series)
rate(mongodb_op_counters_total{type="insert"}[5m])
rate(mongodb_op_counters_total{type="update"}[5m])
rate(mongodb_op_counters_total{type="delete"}[5m])

# Connection Saturation Panel (Gauge)
mongodb_connections{state="current"} / scalar(mongodb_connections{state="available"}) * 100
```

### 3. Container Resource Usage

```promql
# Container CPU Usage
sum(rate(container_cpu_usage_seconds_total[5m]))

# Container Memory Usage
sum(container_memory_usage_bytes)
```

## Creating Advanced Visualization Panels

### MongoDB Query-to-Write Ratio

This helps understand the read/write pattern of your vector database:

```promql
# Panel Title: Query-to-Write Ratio
# Panel Type: Time series
# Formula:
rate(mongodb_op_counters_total{type="query"}[5m]) / 
(rate(mongodb_op_counters_total{type="insert"}[5m]) + rate(mongodb_op_counters_total{type="update"}[5m]))
```

### System Resource Correlation

This panel helps identify how database operations impact system resources:

```promql
# Panel Title: CPU vs DB Operations
# Panel Type: Time series with multiple queries
# Query A: CPU Usage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
# Query B: DB Operations
sum(rate(mongodb_op_counters_total[5m]))
```

## Setting Up Alerts

Configure the following alerts to monitor system health:

1. **High CPU Usage Alert**
   - Query: `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80`
   - Threshold: If CPU usage exceeds 80% for more than 5 minutes
   - This alert helps identify when your vector processing is causing high CPU load

2. **MongoDB Connection Saturation**
   - Query: `mongodb_connections{state="current"} / scalar(mongodb_connections{state="available"}) * 100 > 80`
   - Threshold: If connection usage exceeds 80% for more than 2 minutes
   - This helps prevent connection issues during high-throughput document processing

3. **Memory Usage Alert**
   - Query: `(node_memory_MemTotal_bytes - node_memory_MemFree_bytes) / node_memory_MemTotal_bytes * 100 > 85`
   - Threshold: If memory usage exceeds 85% for more than 5 minutes
   - Critical for vector embedding operations which are memory-intensive

## Dashboard Organization

Organize your dashboard into these sections:

1. **Overview Row**: High-level metrics showing system and application health
2. **Database Performance Row**: MongoDB metrics
3. **System Resources Row**: Detailed CPU, memory, and disk metrics
4. **Container Resources Row**: Container-specific metrics

## Metric Retention and Sampling

For optimal performance:

- Use `[5m]` intervals for most rate calculations (balances detail and performance)
- Keep dashboards focused on a 6-hour time window by default
- Use the "Compare to" feature in Grafana to compare current metrics with previous periods

## Next Steps for Advanced Monitoring

As your ArXiv pipeline evolves:

1. Add custom application metrics for tracking:
   - Document processing times
   - Vector embedding generation performance
   - Query performance in your similarity search system

2. Create dashboards specific to each pipeline component:
   - Document ingestion monitoring
   - Vector database performance
   - Retrieval efficiency metrics

3. Use variables in Grafana to create dynamic dashboards:
   - Filter by specific containers or services
   - Change time ranges easily
   - Toggle between different metric types
