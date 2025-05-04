# Prometheus Queries for ArXiv Pipeline

This document provides a collection of verified Prometheus queries for monitoring the ArXiv Deep Research Pipeline. All queries in this document have been tested and confirmed to work with our specific monitoring setup as of May 4, 2025. Use these queries in Prometheus directly or when creating Grafana dashboards.

## Table of Contents
- [System Metrics](#system-metrics)
- [Container Metrics](#container-metrics)
- [MongoDB Metrics](#mongodb-metrics)
- [Network Metrics](#network-metrics)
- [Application Metrics](#application-metrics)
- [Resource Utilization Alerts](#resource-utilization-alerts)
- [Common PromQL Functions](#common-promql-functions)
- [Troubleshooting](#troubleshooting)

## System Metrics

### CPU Usage

```promql
# CPU usage percentage per core
100 - (avg by (instance, cpu) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Overall CPU usage percentage
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# CPU usage by mode (user, system, iowait)
sum by (mode) (irate(node_cpu_seconds_total{mode!="idle"}[5m]))
```

### Memory Usage

```promql
# Memory usage percentage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Memory usage in bytes
node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes

# Memory usage by application
sum(container_memory_usage_bytes) by (name)
```

### Disk Usage

```promql
# Disk space usage percentage by mount point
100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100)

# Disk I/O operations
rate(node_disk_io_time_seconds_total[5m])

# Disk read/write bytes per second
rate(node_disk_read_bytes_total[5m])
rate(node_disk_written_bytes_total[5m])
```

### System Load

```promql
# System load average (1m, 5m, 15m)
node_load1
node_load5
node_load15

# System load per CPU
node_load1 / count without(cpu, mode) (node_cpu_seconds_total{mode="idle"})
```

## Container Metrics

### Container Names and IDs Quick Reference

```promql
# MongoDB: arxiv_pipeline-mongodb-1 (ID: 19e75134f25f)
# Neo4j: arxiv_pipeline-neo4j-1 (ID: 72fade2b4927)
# Web UI: arxiv_pipeline-web-ui-1 (ID: 03defca167e2)
# Sync Neo4j: arxiv_pipeline-sync-neo4j-1 (ID: 3c229f261e6d)
# MongoDB Exporter: arxiv_pipeline-mongodb-exporter-1 (ID: 92eb39fc599a)
```

⚠️ **IMPORTANT**: Use container names (e.g., `name="arxiv_pipeline-mongodb-1"`) instead of raw IDs for most reliable results. See [container_id_reference.md](./container_id_reference.md) for detailed options.

### Container CPU Usage

```promql
# Total CPU usage by container
sum by (id) (rate(container_cpu_usage_seconds_total[5m]))

# CPU usage by MongoDB container
rate(container_cpu_usage_seconds_total{id="19e75134f25f"}[5m])

# CPU usage by Neo4j container
rate(container_cpu_usage_seconds_total{id="72fade2b4927"}[5m])

# Top 5 containers by CPU usage
topk(5, sum by (id) (rate(container_cpu_usage_seconds_total[5m])))
```

### Container Memory Usage

```promql
# Memory usage by container
container_memory_usage_bytes

# Memory usage by MongoDB container
container_memory_usage_bytes{id="19e75134f25f"}

# Memory usage by Neo4j container
container_memory_usage_bytes{id="72fade2b4927"}

# Memory usage by Web UI container
container_memory_usage_bytes{id="03defca167e2"}

# Memory usage trend over time for MongoDB
container_memory_usage_bytes{id="19e75134f25f"}[30m:1m]
```

### Container Network Usage

```promql
# Network received bytes (overall)
rate(container_network_receive_bytes_total[5m])

# Network transmitted bytes (overall)
rate(container_network_transmit_bytes_total[5m])

# Network received bytes for MongoDB container
rate(container_network_receive_bytes_total{id="19e75134f25f"}[5m])

# Network transmitted bytes for MongoDB container
rate(container_network_transmit_bytes_total{id="19e75134f25f"}[5m])

# Network received bytes for Neo4j container
rate(container_network_receive_bytes_total{id="72fade2b4927"}[5m])
```

### Container Lifecycle

```promql
# Container uptime in seconds
time() - container_start_time_seconds

# For other lifecycle metrics, check what's available with:
{__name__=~"container_.*start.*"}
```

## MongoDB Metrics

### MongoDB Operation Metrics

```promql
# Operations per second by type
rate(mongodb_op_counters_total[5m])

# Query operations per second
rate(mongodb_op_counters_total{type="query"}[5m])

# Insert operations per second
rate(mongodb_op_counters_total{type="insert"}[5m])
```

### MongoDB Connection Metrics

```promql
# Current connections
mongodb_connections{state="current"}

# Available connections
mongodb_connections{state="available"}

# MongoDB network metrics (bytes in/out)
rate(mongodb_network_bytes_total[5m])

# MongoDB query performance (95th percentile execution time)
histogram_quantile(0.95, sum(rate(mongodb_mongod_db_query_execution_time_ms_bucket[5m])) by (le))
```

### MongoDB Performance Metrics

```promql
# MongoDB query execution time (if available)
histogram_quantile(0.95, sum(rate(mongodb_mongod_db_query_execution_time_ms_bucket[5m])) by (le))

# MongoDB page fault rate
rate(mongodb_extra_info_page_faults_total[5m])
```

## Network Metrics

### Network Traffic

```promql
# Network interface traffic in bytes per second
rate(node_network_receive_bytes_total[5m])
rate(node_network_transmit_bytes_total[5m])

# Total network traffic across all interfaces
sum(rate(node_network_receive_bytes_total[5m]))
sum(rate(node_network_transmit_bytes_total[5m]))
```

### Network Errors

```promql
# Network interface errors per second
rate(node_network_receive_errs_total[5m])
rate(node_network_transmit_errs_total[5m])

# Packet drops
rate(node_network_receive_drop_total[5m])
rate(node_network_transmit_drop_total[5m])
```

### TCP Connections

```promql
# TCP connection states
node_netstat_Tcp_CurrEstab
sum by (state) (node_netstat_Tcp_InSegs)
```

## Application Metrics

These metrics assume you've instrumented your application with the Prometheus client library. Below are examples of what you might track in your ArXiv pipeline:

```promql
# Total papers processed
papers_processed_total

# Paper processing rate
rate(papers_processed_total[5m])

# Processing time histogram (95th percentile)
histogram_quantile(0.95, sum(rate(vector_processing_seconds_bucket[5m])) by (le))

# Processing success rate
rate(papers_processed_total{status="success"}[5m]) / rate(papers_processed_total[5m])

# Database operation latency
histogram_quantile(0.95, sum(rate(database_operation_duration_seconds_bucket[5m])) by (le, operation))
```

## Resource Utilization Alerts

These queries can be used for alerting when resources reach critical levels:

```promql
# High CPU utilization alert
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85

# High memory utilization alert
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90

# Disk space critical alert
(node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100 < 10

# MongoDB connection saturation (if mongodb_connections metrics are available)
mongodb_connections{state="current"} / mongodb_connections{state="available"} > 0.8

# Container memory usage alert
sum(container_memory_usage_bytes) by (id) / scalar(sum(machine_memory_bytes)) * 100 > 80
```

## Common PromQL Functions

- `rate()`: Calculate per-second rate of increase of a counter over a time window
- `irate()`: Calculate instant per-second rate of increase of a counter over the last two data points
- `increase()`: Calculate increase in value over a time window
- `sum()`: Aggregate values
- `avg()`: Calculate average of values
- `max()`: Find maximum value
- `min()`: Find minimum value
- `topk()`: Select top k elements by value
- `bottomk()`: Select bottom k elements by value
- `histogram_quantile()`: Calculate quantile from histogram
- `count()`: Count number of elements
- `by()`: Group aggregation by labels
- `without()`: Group aggregation without specified labels

---

## Troubleshooting

If you're not seeing data for some queries, try these steps:

### Container Label Issues

If container queries using pattern matching (like `{name=~".*mongo.*"}`) aren't returning data, the issue is likely with the labels:

```promql
# Instead of using name label which might not exist:
# container_memory_usage_bytes{name=~".*mongo.*"}

# Try using the exact container ID (most reliable):
container_memory_usage_bytes{id="19e75134f25f"}

# Or try alternative labels that might exist:
container_memory_usage_bytes{image=~".*mongo.*"}
container_memory_usage_bytes{container_name=~".*mongo.*"}
```

### Check Available Labels

To see which labels actually exist for a particular metric:

```promql
# View all labels for container metrics
container_memory_usage_bytes{}

# View all available metrics with 'mongo' in any label
{__name__=~".+", =~".*mongo.*"}
```

### Discover Available Metrics

```promql
# List all metrics
{__name__=~".+"}

# Find specific types of metrics
{__name__=~"container_.*"}
{__name__=~"node_.*"}
{__name__=~"mongodb_.*"}
```

### Check Container IDs

```promql
# Get a list of all container IDs
container_memory_usage_bytes
```

### Examine All Labels for a Metric

```promql
# View all labels for a specific metric
container_memory_usage_bytes{}
```

## Using These Queries in Grafana

1. Add a new panel in Grafana
2. Select Prometheus as the data source
3. Copy and paste the desired query into the PromQL query editor
4. Adjust time range as needed
5. Format the visualization (Graph, Gauge, Table, etc.)

These queries provide a starting point and can be adjusted based on specific monitoring needs for the ArXiv pipeline project.
