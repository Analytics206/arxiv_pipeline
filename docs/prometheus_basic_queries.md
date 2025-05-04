# Prometheus Basic Queries

This document provides simple, verified queries to help you explore and troubleshoot the ArXiv pipeline monitoring system.

## Core Metrics

These fundamental queries have been confirmed to work in our environment:

```promql
# Check which targets are up (1) or down (0)
up

# See how many metrics are being collected per target
scrape_samples_scraped
```

## Label Troubleshooting

If your queries aren't returning data, you might be using the wrong labels. Here's how to discover what labels are actually available:

```promql
# Show all available labels for container metrics
container_memory_usage_bytes{}

# Show all values for the 'id' label
count by (id) (container_memory_usage_bytes)

# Show what labels exist for container metrics
label_names({__name__="container_memory_usage_bytes"})

# Find metrics related to MongoDB in any way
{__name__=~".+", image=~".*mongo.*"}
```

### Common Label Issues

1. **Missing `name` Label**: If `container_memory_usage_bytes{name=~".*mongo.*"}` returns no data, the `name` label might not exist. Try these alternatives:

```promql
# Search by image name instead
container_memory_usage_bytes{image=~".*mongo.*"}

# See what container-identifying labels are available
container_memory_usage_bytes{}
```

2. **Container ID Format Issues**: The Docker short IDs often need to be in a specific format for cAdvisor/Prometheus:

```promql
# Try these ID formats instead of bare IDs
# Format 1: Full Docker format
container_memory_usage_bytes{id="/docker/19e75134f25f"}

# Format 2: Docker compose format
container_memory_usage_bytes{name="arxiv_pipeline-mongodb-1"}

# Format 3: Container name pattern
container_memory_usage_bytes{name=~".*mongodb.*"}
```

3. **Finding the Right Format**: To discover which format your system uses:

```promql
# List all container metrics (look at the id and name fields)
container_memory_usage_bytes

# List all values for the id label
count by (id) (container_memory_usage_bytes)

# List all values for container names
count by (name) (container_memory_usage_bytes)
```

2. **Label Format Differences**: Sometimes labels are formatted differently than expected:

```promql
# Try different variations
container_memory_usage_bytes{container_name=~".*mongo.*"}
container_memory_usage_bytes{container=~".*mongo.*"}
```

## Discover Available Metrics

```promql
# List all available metrics (use in Prometheus UI)
{__name__=~".+"}

# Check available labels for a specific metric (replace metric_name)
{__name__="metric_name"}
```

## System Metrics Basics

```promql
# Basic CPU metric
node_cpu_seconds_total

# Memory info
node_memory_MemTotal_bytes
node_memory_MemFree_bytes

# Disk space
node_filesystem_size_bytes
node_filesystem_avail_bytes
```

## Container Metrics Basics

```promql
# Check what container metrics exist
container_cpu_usage_seconds_total

# List all container names
count(container_cpu_usage_seconds_total) by (name)

# Memory usage (adjust container name as needed)
container_memory_usage_bytes
```

## MongoDB Metrics Basics

```promql
# Check if MongoDB exporter is working
mongodb_up

# Basic MongoDB metrics
mongodb_connections
mongodb_op_counters_total
```

## Network Metrics Basics

```promql
# Check network metrics
node_network_up
node_network_info

# Network bytes
node_network_receive_bytes_total
node_network_transmit_bytes_total
```

## Troubleshooting Tips

1. **Check Target Status**: In Prometheus UI, go to Status → Targets to see if all exporters are UP
2. **Check Scrape Configuration**: Verify prometheus.yml has the correct targets and job names
3. **Check Time Range**: Make sure the time range in Prometheus UI includes when metrics were collected
4. **Use Metrics Explorer**: In Prometheus UI, use the "Graph" tab with auto-complete to discover metrics
5. **Check Container Names**: The actual container names may be different from what's in the queries

## Simplified Queries for ArXiv Pipeline

Once you identify the available metrics, you can create more specific queries. Here are some simplified examples:

```promql
# CPU usage of all containers
sum by (name) (rate(container_cpu_usage_seconds_total[5m]))

# Memory usage of all containers
sum by (name) (container_memory_usage_bytes)

# Disk space available percentage
100 * (node_filesystem_avail_bytes / node_filesystem_size_bytes)

# MongoDB operations (if available)
rate(mongodb_op_counters_total[5m])
```

Start with these basic queries to verify that metrics are being collected, then gradually move to more complex queries as you confirm which metrics are available in your environment.
