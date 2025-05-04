# Container ID Reference for Prometheus Queries

This document serves as a reference for container and system IDs available in the ArXiv Pipeline monitoring system. Use these IDs when crafting Prometheus queries to target specific containers or system components.

## ID Structure and Patterns

The IDs follow a hierarchical structure representing the Linux cgroups architecture:

- System components use `/system.slice/...` format
- User processes use `/user.slice/...` format
- Docker containers typically appear directly under `/docker`

## Available IDs

### Root and Top-Level Containers

```
{id="/"}                     # Root container (entire system)
{id="/docker"}               # All Docker containers
{id="/kubepods"}             # Kubernetes pods (if applicable)
{id="/podruntime"}           # Pod runtime environment
{id="/init.scope"}           # System initialization
```

### System Services

```
{id="/system.slice"}                                    # All system services
{id="/system.slice/docker.service"}                     # Docker service
{id="/system.slice/containerd.service"}                 # Container runtime
{id="/system.slice/systemd-journald.service"}           # System logging
{id="/system.slice/systemd-resolved.service"}           # DNS resolution
{id="/system.slice/systemd-timesyncd.service"}          # Time synchronization
{id="/system.slice/systemd-udevd.service"}              # Device management
{id="/system.slice/systemd-logind.service"}             # Login management
{id="/system.slice/dbus.service"}                       # D-Bus messaging system
{id="/system.slice/rsyslog.service"}                    # System logging
{id="/system.slice/cron.service"}                       # Scheduled tasks
{id="/system.slice/polkit.service"}                     # Authentication framework
{id="/system.slice/snapd.socket"}                       # Snap package manager
{id="/system.slice/unattended-upgrades.service"}        # Automatic updates
{id="/system.slice/console-getty.service"}              # Console management
{id="/system.slice/docker.socket"}                      # Docker API socket
{id="/system.slice/motd-news.service"}                  # Message of the day
{id="/system.slice/wsl-pro.service"}                    # WSL service (Windows)
```

### System Terminal and Login

```
{id="/system.slice/system-getty.slice"}                             # Terminal services
{id="/system.slice/system-getty.slice/getty@tty1.service"}          # Terminal 1
{id="/system.slice/system-modprobe.slice"}                          # Kernel module loading
```

### User Processes

```
{id="/user.slice"}                                                   # All user processes
{id="/user.slice/user-0.slice"}                                      # Root user (0)
{id="/user.slice/user-0.slice/session-3.scope"}                      # Root user session 3
{id="/user.slice/user-0.slice/user@0.service"}                       # Root user service
{id="/user.slice/user-0.slice/user@0.service/app.slice"}             # Root user applications
{id="/user.slice/user-0.slice/user@0.service/app.slice/dbus.socket"} # Root user D-Bus
{id="/user.slice/user-0.slice/user@0.service/init.scope"}            # Root user initialization
{id="/user.slice/user-1000.slice"}                                   # Regular user (1000)
{id="/user.slice/user-1000.slice/session-1.scope"}                   # User 1000 session 1
{id="/user.slice/user-1000.slice/user@1000.service"}                 # User 1000 service
```

## Using IDs in Queries

### Basic Usage

```promql
# Get CPU usage for Docker service
sum(rate(container_cpu_usage_seconds_total{id="/system.slice/docker.service"}[5m]))

# Get memory usage for all Docker containers
sum(container_memory_usage_bytes{id="/docker"})
```

### Partial Matching with Regular Expressions

```promql
# All system services
sum by (id) (container_memory_usage_bytes{id=~"/system\\.slice/.*"})

# All user processes
sum by (id) (container_memory_usage_bytes{id=~"/user\\.slice/.*"})
```

### Combining with Other Labels

```promql
# Filter by both ID and another label if available
sum(rate(container_cpu_usage_seconds_total{id="/docker", image=~".*mongodb.*"}[5m]))
```

### Comparing Docker vs System Resources

```promql
# CPU usage comparison between Docker and system services
sum(rate(container_cpu_usage_seconds_total{id="/docker"}[5m])) / 
sum(rate(container_cpu_usage_seconds_total{id=~"/system\\.slice/.*"}[5m])) * 100
```

## Finding ArXiv Pipeline Containers

The IDs shown above are primarily system-level containers, not your Docker application containers. Docker containers created by docker-compose have different ID formats that aren't appearing in this list.

To find your specific Docker container IDs for the ArXiv pipeline services (MongoDB, Neo4j, etc.), try these approaches:

### 1. Check Other Container Labels

Docker container metrics typically have additional labels beyond just `id`. Try examining other labels:

```promql
# Show all labels available for container metrics
container_memory_usage_bytes
```

Look for labels like `name`, `image`, or `container_name` that might help identify your services.

### 2. Use Container Name Pattern Matching

If container names are available, try:

```promql
# Find MongoDB containers
container_memory_usage_bytes{name=~".*mongo.*"}

# Find Neo4j containers
container_memory_usage_bytes{name=~".*neo4j.*"}
```

### 3. Use Docker Commands to Map Container IDs

You can map Docker container IDs to Prometheus metrics by:

```powershell
# List Docker containers with their IDs
docker ps --format "{{.ID}} {{.Names}}"
```

Then look for these IDs or patterns in your Prometheus metrics.

### 4. Check Docker-Specific Metrics

Some metrics might be specific to Docker containers:

```promql
# Look for Docker-specific metrics
{__name__=~"docker_.*"}
```

## ArXiv Pipeline Container IDs

Below are the actual container IDs and names for the ArXiv pipeline services.

⚠️ **IMPORTANT: Container ID Format**

The format for container IDs in Prometheus/cAdvisor may vary. Try these formats if the metrics aren't appearing:

```promql
# Option 1: Using container names (most reliable)
container_memory_usage_bytes{name="arxiv_pipeline-mongodb-1"}

# Option 2: Using Docker format with ID prefixes
container_memory_usage_bytes{id="/docker/19e75134f25f"}

# Option 3: Using Docker container name patterns
container_memory_usage_bytes{name=~".*mongodb.*"}
```

### Main Application Containers

```promql
# MongoDB container
{name="arxiv_pipeline-mongodb-1"} # ID: 19e75134f25f

# Neo4j container
{name="arxiv_pipeline-neo4j-1"} # ID: 72fade2b4927

# Web UI container
{name="arxiv_pipeline-web-ui-1"} # ID: 03defca167e2

# Sync Neo4j service
{name="arxiv_pipeline-sync-neo4j-1"} # ID: 3c229f261e6d
```

### Monitoring Stack Containers

```promql
# Grafana
{name="arxiv_pipeline-grafana-1"} # ID: 540c3fb7b7a0

# Prometheus
{name="arxiv_pipeline-prometheus-1"} # ID: 01edd2def561

# Node Exporter
{name="arxiv_pipeline-node-exporter-1"} # ID: a760add85e8b

# cAdvisor
{name="arxiv_pipeline-cadvisor-1"} # ID: 46531cfed3b5

# MongoDB Exporter
{name="arxiv_pipeline-mongodb-exporter-1"} # ID: 92eb39fc599a
```

---

**Note**: This document is based on the ID structure observed in your specific environment and may need updates as your infrastructure changes.
