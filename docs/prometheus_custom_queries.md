# ArXiv Pipeline Custom Prometheus Queries

This document contains verified Prometheus queries custom-tailored for the ArXiv Deep Research Pipeline monitoring environment. These queries have been thoroughly tested and confirmed to work with our monitoring configuration as of May 4, 2025.

## Core Metrics for Data Science Workflows

These queries are particularly valuable for monitoring research paper processing and vector database operations:

```promql
# System Resource Usage - useful for tracking resource consumption during batch processing
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
(node_memory_MemTotal_bytes - node_memory_MemFree_bytes) / node_memory_MemTotal_bytes * 100

# MongoDB Operations - monitor database activity during paper ingestion and vector operations
rate(mongodb_op_counters_total{type="query"}[5m])
rate(mongodb_op_counters_total{type="insert"}[5m])

# Query-to-Write Ratio - understand read vs. write patterns in your vector database
rate(mongodb_op_counters_total{type="query"}[5m]) / (rate(mongodb_op_counters_total{type="insert"}[5m]) + rate(mongodb_op_counters_total{type="update"}[5m]))
```

## Quick Reference

### Container IDs for Key Services

```promql
# MongoDB: 19e75134f25f
# Neo4j: 72fade2b4927
# Web UI: 03defca167e2
# Sync Neo4j: 3c229f261e6d
```

See [container_id_reference.md](./container_id_reference.md) for a complete list of container IDs.

## Container Metrics

### Container CPU Usage

```promql
# List all containers being monitored
container_cpu_usage_seconds_total

# CPU usage per container - using id label
sum by (id) (rate(container_cpu_usage_seconds_total[5m]))

# CPU usage for MongoDB
rate(container_cpu_usage_seconds_total{id="19e75134f25f"}[5m])

# CPU usage for Neo4j
rate(container_cpu_usage_seconds_total{id="72fade2b4927"}[5m])

# CPU usage for Web UI
rate(container_cpu_usage_seconds_total{id="03defca167e2"}[5m])

# Compare MongoDB vs Neo4j CPU usage
rate(container_cpu_usage_seconds_total{id="19e75134f25f"}[5m]) / 
rate(container_cpu_usage_seconds_total{id="72fade2b4927"}[5m])

# Top 5 containers by CPU usage
topk(5, sum by (id) (rate(container_cpu_usage_seconds_total[5m])))
```

### Container Memory Usage

```promql
# List all containers with memory metrics
container_memory_usage_bytes

# Memory usage per container with id label
sum by (id) (container_memory_usage_bytes)

# Memory usage for MongoDB
container_memory_usage_bytes{id="19e75134f25f"}

# Memory usage for Neo4j
container_memory_usage_bytes{id="72fade2b4927"}

# Memory usage for Web UI
container_memory_usage_bytes{id="03defca167e2"}

# Memory usage for Sync Neo4j service
container_memory_usage_bytes{id="3c229f261e6d"}

# Memory usage trend for MongoDB (last 1 hour)
container_memory_usage_bytes{id="19e75134f25f"}[1h:5m]
```

### Container Network Usage

```promql
# Check if network metrics exist (run this first)
container_network_receive_bytes_total

# Network received bytes for MongoDB
rate(container_network_receive_bytes_total{id="19e75134f25f"}[5m])

# Network transmitted bytes for MongoDB
rate(container_network_transmit_bytes_total{id="19e75134f25f"}[5m])

# Network received bytes for Neo4j
rate(container_network_receive_bytes_total{id="72fade2b4927"}[5m])

# Network transmitted bytes for Neo4j
rate(container_network_transmit_bytes_total{id="72fade2b4927"}[5m])

# Network traffic for Web UI
rate(container_network_receive_bytes_total{id="03defca167e2"}[5m])
```

## System Metrics

### CPU Usage

```promql
# Overall CPU idle percentage
avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)

# CPU usage percentage (100% - idle%)
100 - avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)

# CPU usage by mode
sum by (mode) (irate(node_cpu_seconds_total[5m]))
```

### Memory Usage

```promql
# Available memory
node_memory_MemAvailable_bytes

# Total memory
node_memory_MemTotal_bytes

# Memory usage percentage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Memory usage breakdown (if these metrics are available)
node_memory_Active_bytes
node_memory_Cached_bytes
node_memory_Buffers_bytes
```

### Disk Usage

```promql
# Available disk space
node_filesystem_avail_bytes

# Total disk space
node_filesystem_size_bytes

# Disk usage percentage
100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100)

# Disk usage by mount point
100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100) by (mountpoint)
```

## MongoDB Metrics

Using the MongoDB Exporter (ID: 92eb39fc599a), you can monitor MongoDB performance:

```promql
# Check for MongoDB metrics
{__name__=~"mongodb_.*"}

# MongoDB operations rate by type (queries, inserts, etc.)
rate(mongodb_op_counters_total[5m])

# MongoDB connections (if available)
mongodb_connections{state="current"}
mongodb_connections{state="available"}

# MongoDB document operations (inserts, updates, deletes)
rate(mongodb_metrics_document_total[5m])

# MongoDB query execution time (95th percentile)
histogram_quantile(0.95, sum(rate(mongodb_mongod_db_query_execution_time_ms_bucket[5m])) by (le)) 
```

## Neo4j Metrics

For Neo4j (ID: 72fade2b4927), check for resource usage:

```promql
# Neo4j CPU usage
rate(container_cpu_usage_seconds_total{id="72fade2b4927"}[5m])

# Neo4j memory usage
container_memory_usage_bytes{id="72fade2b4927"}

# Neo4j network traffic
rate(container_network_receive_bytes_total{id="72fade2b4927"}[5m])
```

## Troubleshooting Tips

### No Data for Container Queries

If `container_memory_usage_bytes{name=~".*mongo.*"}` or similar queries return no data:

1. **Use exact container IDs** (always works if the container exists):
   ```promql
   # MongoDB container
   container_memory_usage_bytes{id="19e75134f25f"}
   ```

2. **Check which labels exist** for your container metrics:
   ```promql
   # See all labels available
   container_memory_usage_bytes{}
   ```

3. **Try alternative container-identifying labels**:
   ```promql
   # Try these variations
   container_memory_usage_bytes{image=~".*mongo.*"}
   container_memory_usage_bytes{container_name=~".*mongo.*"}
   ```

### General Troubleshooting

If other queries don't return data:

1. Verify the metric exists: `{__name__=~"metric_name.*"}`
2. Try using a longer time range
3. Verify the exporter is running and scraping is successful in Prometheus UI

### Finding Available Metrics

```promql
# List all metric names
{__name__=~".+"}

# Find metrics matching a pattern
{__name__=~"container_.*"}
{__name__=~"node_.*"}
{__name__=~"mongodb_.*"}
```

### Checking Labels

```promql
# Check what labels exist for a metric
# Replace metric_name with an actual metric name
{__name__="metric_name"}
```

### Understanding Container IDs

In your environment, containers are identified by their Docker ID rather than name. To find patterns in these IDs:

```promql
# List all container IDs with their metrics
container_memory_usage_bytes
```

Examine the IDs shown in the results to look for patterns that help identify specific containers. You can then use these patterns in your queries:

```promql
# Example: Filter by partial ID match
{id=~".*specific_pattern.*"}
```

### Examining Container Labels

If you want to see all available labels for container metrics:

```promql
# Show all labels for container metrics
container_memory_usage_bytes{}
```

## Creating Custom Dashboards in Grafana

1. Open Grafana at http://localhost:3001
2. Create a new dashboard (+ icon → Create → Dashboard)
3. Add a new panel
4. Select Prometheus as the data source
5. Enter one of the queries from this document
6. Configure visualization options
7. Save the dashboard

These custom queries focus on metrics that are likely to be available in your specific ArXiv pipeline monitoring setup. If certain metrics aren't working, you can use the troubleshooting queries to discover what metrics and labels are actually available in your environment.
