# Prometheus Container ID Format Guide

This document explains the specific container ID format used in the ArXiv Pipeline's Prometheus monitoring setup.

## ID Format Discovery

Our monitoring diagnostic has discovered that the cAdvisor in our setup reports containers with the following ID format:

```
/system.slice/docker.service
/system.slice/docker.socket
/system.slice/containerd.service
/docker
```

Rather than using Docker container names or raw container IDs, our cAdvisor implementation uses system-level paths.

## Working Queries by Component Type

### Docker Service (General Docker Metrics)

```promql
# Docker service CPU
rate(container_cpu_usage_seconds_total{id="/system.slice/docker.service"}[5m])

# Docker service memory
container_memory_usage_bytes{id="/system.slice/docker.service"}
```

### Docker Containers (Aggregated)

```promql
# All Docker containers CPU
rate(container_cpu_usage_seconds_total{id="/docker"}[5m])

# All Docker containers memory
container_memory_usage_bytes{id="/docker"}
```

### Container Runtime

```promql
# Containerd CPU usage
rate(container_cpu_usage_seconds_total{id="/system.slice/containerd.service"}[5m])

# Containerd memory usage
container_memory_usage_bytes{id="/system.slice/containerd.service"}
```

### System-wide Metrics

```promql
# Overall CPU usage (all containers)
sum by (instance)(rate(container_cpu_usage_seconds_total[5m]))

# Overall memory usage (all containers)
sum(container_memory_usage_bytes) by (instance)
```

## Host System Metrics

These metrics work regardless of container ID format:

```promql
# CPU usage percentage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)

# Memory usage percentage
(node_memory_MemTotal_bytes - node_memory_MemFree_bytes - node_memory_Cached_bytes) / node_memory_MemTotal_bytes * 100

# Disk usage percentage 
100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes)
```

## MongoDB-Specific Metrics

These metrics are provided by the MongoDB exporter and don't rely on container IDs:

```promql
# MongoDB operations rate
rate(mongodb_op_counters_total[5m])

# MongoDB connections
mongodb_connections{state="current"}
mongodb_connections{state="available"}
```

## Network Metrics

```promql
# All network traffic received
rate(container_network_receive_bytes_total[5m])

# Docker-specific network traffic
rate(container_network_receive_bytes_total{id="/docker"}[5m])
```

## Troubleshooting Missing Data

If your Grafana dashboard or Prometheus queries aren't showing data:

1. Run the diagnostic script to check available metrics:
   ```bash
   python scripts/check_prometheus_metrics.py
   ```

2. Check what container ID format your system uses:
   ```promql
   container_memory_usage_bytes
   ```

3. Look at the `id` field in the results and use that format in your queries.
