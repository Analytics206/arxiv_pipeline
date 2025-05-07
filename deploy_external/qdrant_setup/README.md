# 🔍 External Qdrant GPU Server Setup (Local Network)

This guide provides instructions for setting up Qdrant with GPU support on a separate machine within the same network. This standalone configuration enhances vector search performance using GPU acceleration through WSL2 and Docker, optimized for high-performance vector similarity search.

## Table of Contents
- [Prerequisites](#prerequisites)
- [WSL2 GPU Setup](#wsl2-gpu-setup)
- [Docker GPU Setup](#docker-gpu-setup)
- [Qdrant Configuration](#qdrant-configuration)
- [Connecting to Qdrant](#connecting-to-qdrant)
- [Performance Tuning](#performance-tuning)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Windows 11** with:
  - NVIDIA GPU (RTX series recommended for best performance)
  - NVIDIA display drivers installed ([Download Latest](https://www.nvidia.com/download/index.aspx))
  - Administrator access
- **Minimum Hardware**:
  - 16GB RAM (32GB recommended)
  - NVIDIA GPU with CUDA support (8GB VRAM minimum)
  - SSD storage with 100GB+ free space
- **Network**:
  - Static IP address on the local network
  - Ability to open ports 6333 and 6334

---

## WSL2 GPU Setup

### 1. Install and Configure WSL2

```powershell
# In PowerShell with Administrator privileges

# Install WSL2 with Ubuntu
wsl --install -d Ubuntu

# Ensure you're using WSL2
wsl --set-default-version 2
wsl --set-version Ubuntu 2

# Verify WSL2 installation
wsl -l -v
```

### 2. Configure WSL2 Memory Allocation

Create or edit the WSL2 configuration file to optimize memory allocation for GPU operations:

```powershell
# Create/edit .wslconfig in your Windows user profile directory
notepad "$env:USERPROFILE\.wslconfig"
```

Add the following content to the file:

```
[wsl2]
memory=16GB
processors=4
swap=8GB
localhostForwarding=true
```

### 3. Install NVIDIA CUDA Driver for WSL2

1. Download the NVIDIA CUDA Driver for WSL2: [NVIDIA CUDA on WSL](https://developer.nvidia.com/cuda/wsl)
2. Run the installer and follow the prompts
3. Restart your computer after installation

### 4. Verify GPU Access in WSL2

```bash
# Inside Ubuntu WSL2

# Update package information
sudo apt update

# Install NVIDIA utilities
sudo apt install -y nvidia-cuda-toolkit

# Verify NVIDIA driver is accessible
nvidia-smi
```

You should see output showing your GPU information and driver version. If not, verify your NVIDIA drivers are properly installed.

## Docker GPU Setup

### 1. Install Docker in WSL2

```bash
# Inside Ubuntu WSL2

# Remove any existing Docker installations
sudo apt-get remove docker docker-engine docker.io containerd runc

# Set up Docker repository
sudo apt-get update
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add your user to the docker group to run Docker without sudo
sudo usermod -aG docker $USER

# Apply the changes
newgrp docker
```

### 2. Install NVIDIA Container Toolkit

```bash
# Inside Ubuntu WSL2

# Add NVIDIA package repositories
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Restart Docker daemon
sudo systemctl restart docker

# Verify NVIDIA Container Toolkit installation
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

You should see the same GPU information that you saw when running `nvidia-smi` directly in WSL2.
## Qdrant Configuration

### 1. Download the Deployment Files

First, create a working directory for your Qdrant deployment:

```bash
# Inside Ubuntu WSL2
mkdir -p ~/qdrant-gpu-server
cd ~/qdrant-gpu-server
```

Create the necessary files for deployment (or download them from your source repository):

### 2. Create Docker Compose Configuration

Create a file named `docker-compose.yml` with the following content:

```yaml
version: '3.8'

services:
  qdrant:
    build: .
    container_name: qdrant-server
    ports:
      - "6333:6333"  # HTTP
      - "6334:6334"  # gRPC
    volumes:
      - qdrant_storage:/qdrant/storage
      - ./config:/qdrant/config
    environment:
      - QDRANT_LOG_LEVEL=INFO
      - RUST_LOG=info
      - CUDA_VISIBLE_DEVICES=0  # Specify which GPU to use (0 is first GPU)
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

volumes:
  qdrant_storage:
```

### 3. Create Dockerfile

Create a file named `Dockerfile` with the following content:

```dockerfile
# Start from the CUDA base image
FROM nvidia/cuda:12.0.1-devel-ubuntu22.04 AS builder

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Clone Qdrant repository
WORKDIR /qdrant
RUN git clone https://github.com/qdrant/qdrant.git .

# Build with GPU support
ENV CUDA=1
RUN cargo build --release --bin qdrant

# Final image
FROM nvidia/cuda:12.0.1-runtime-ubuntu22.04

# Copy the built Qdrant binary
COPY --from=builder /qdrant/target/release/qdrant /qdrant/qdrant
WORKDIR /qdrant

# Default ports
EXPOSE 6333 6334

# Starting Qdrant
CMD ["./qdrant"]
```

### 4. Create Qdrant Configuration

Create a configuration directory and file:

```bash
# Create config directory
mkdir -p ~/qdrant-gpu-server/config

# Create configuration file
cat > ~/qdrant-gpu-server/config/config.yaml << EOF
log_level: INFO

storage:
  storage_path: /qdrant/storage

service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334

vectors:
  # For typical embeddings from transformers like BERT, etc.
  size: 768
  distance: Cosine
  hnsw_config:
    m: 16
    ef_construct: 100  # Higher values = better recall but slower indexing
    full_scan_threshold: 10000

optimizers:
  # Using GPU for vector operations
  vectors_optimizer_config:
    cpu_budget: 2
    default_segment_number: 5
    max_segment_size: 50000
    memmap_threshold: 10000
    indexing_threshold: 5000
    rescore_type: gpu  # Using GPU for rescoring
EOF
```

### 5. Deploy Qdrant with Docker Compose

```bash
# From the ~/qdrant-gpu-server directory
docker-compose up --build -d
```

This will:
1. Build the Qdrant image with GPU support
2. Start the container with GPU acceleration enabled
3. Mount the configuration and storage volumes
4. Expose the HTTP and gRPC ports

### 6. Verify Deployment

```bash
# Check that the container is running
docker ps

# Check logs for any errors
docker logs qdrant-server

# Test the HTTP API
curl http://localhost:6333/healthz
```

### 7. Open Firewall Ports

```powershell
# In PowerShell (Admin) on Windows:
New-NetFirewallRule -DisplayName "Qdrant HTTP API" -Direction Inbound -LocalPort 6333 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Qdrant gRPC API" -Direction Inbound -LocalPort 6334 -Protocol TCP -Action Allow
```
New-NetFirewallRule -DisplayName "Qdrant gRPC API" -Direction Inbound -LocalPort 6334 -Protocol TCP -Action Allow
```

## Connecting to Qdrant

### 1. Find Your Server's IP Address

You'll need to know the IP address of your Qdrant server to connect to it from other machines on the network:

```bash
# In WSL2:
ip addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'
```

Or in Windows:

```powershell
ipconfig
```

Note the IPv4 address for your network interface.

### 2. Install Python Client

On the machine that will connect to Qdrant (your main application server), install the Qdrant client:

```bash
# In your Python environment
pip install qdrant-client
```

### 2. Test Connection from the ArXiv Pipeline Machine
Create a test script to verify connectivity:

```python
# test_qdrant_connection.py
from qdrant_client import QdrantClient

# Replace with your Qdrant server's IP address
QDRANT_HOST = "192.168.1.x"  # Use the static IP of your Qdrant server
QDRANT_PORT = 6333

def test_connection():
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    health = client.health()
    print(f"Qdrant connection status: {health}")
    collections = client.get_collections()
    print(f"Available collections: {collections}")

if __name__ == "__main__":
    test_connection()
```

### 3. Create Paper Embeddings Collection

Create a Python script to set up your vector collection:

```python
# create_collection.py
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Replace with your Qdrant server's IP address from step 1
QDRANT_HOST = "192.168.1.x"  # Change to your server's actual IP
QDRANT_PORT = 6333

def create_arxiv_collection():
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Create collection for paper embeddings
    client.create_collection(
        collection_name="arxiv_papers",
        vectors_config=models.VectorParams(
            size=768,  # Adjust based on your embedding model
            distance=models.Distance.COSINE
        ),
        optimizers_config=models.OptimizersConfigDiff(
            default_segment_number=5,
            indexing_threshold=20000,
            memmap_threshold=50000,
        )
    )
    
    # Create payload index for efficient filtering
    client.create_payload_index(
        collection_name="arxiv_papers",
        field_name="categories",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    
    client.create_payload_index(
        collection_name="arxiv_papers",
        field_name="year",
        field_schema=models.PayloadSchemaType.INTEGER,
    )
    
    print("Collection 'arxiv_papers' created successfully")

if __name__ == "__main__":
    create_arxiv_collection()
```

### 4. Integration with ArXiv Pipeline Config
When you're ready to connect the ArXiv Pipeline to this Qdrant instance, you'll need to update your config file. Here's an example of what will need to change (do not make these changes yet):

```yaml
# Example future change to config/default.yaml
qdrant:
  host: "192.168.1.x"  # Replace with your Qdrant server's IP
  port: 6333
  collection_name: "arxiv_papers"
```

## Performance Tuning

### 1. Verify Installation
```bash
# Check if Qdrant is running
curl http://localhost:6333/healthz

# Expected output: {"status":"ok"}
```

### 2. Verify GPU Detection
```bash
# Verify CUDA installation
nvidia-smi

# Check GPU utilization during operations
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 5
```

### 3. Performance Testing
Create and run a benchmark script to test search performance:

```python
# benchmark.py
from qdrant_client import QdrantClient
import numpy as np
import time

QDRANT_HOST = "localhost"  # Change to remote host for ArXiv integration
QDRANT_PORT = 6333
COLLECTION_NAME = "benchmark_test"
VECTOR_SIZE = 768

def setup_collection(client):
    from qdrant_client.http import models
    
    # Drop collection if exists
    collections = client.get_collections().collections
    if any(c.name == COLLECTION_NAME for c in collections):
        client.delete_collection(COLLECTION_NAME)
    
    # Create test collection
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE
        )
    )
    
    # Generate random vectors for insertion
    num_vectors = 10000
    vectors = [np.random.rand(VECTOR_SIZE).astype(np.float32) for _ in range(num_vectors)]
    
    # Insert vectors in batches
    batch_size = 1000
    for i in range(0, num_vectors, batch_size):
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=j+i,
                    vector=vectors[j+i-i].tolist(),
                    payload={"metadata": f"vector_{j+i}"}
                ) for j in range(min(batch_size, num_vectors-i))
            ]
        )
    print(f"Inserted {num_vectors} vectors into collection")

def benchmark_search(client, num_queries=100):
    # Generate random query vectors
    queries = [np.random.rand(VECTOR_SIZE).astype(np.float32) for _ in range(num_queries)]
    
    # Measure search time
    start_time = time.time()
    for vector in queries:
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector.tolist(),
            limit=10
        )
    end_time = time.time()
    
    avg_time = (end_time - start_time) / num_queries
    print(f"Average search time: {avg_time*1000:.2f} ms per query")

if __name__ == "__main__":
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    print("Setting up test collection...")
    setup_collection(client)
    
    print("Starting benchmark...")
    benchmark_search(client)
    
    # Cleanup
    client.delete_collection(COLLECTION_NAME)
```

## Maintenance

### 1. Service Management
```bash
# Start Qdrant
sudo systemctl start qdrant

# Stop Qdrant
sudo systemctl stop qdrant

# Restart Qdrant
sudo systemctl restart qdrant

# View Logs
journalctl -u qdrant -f -n 100
```

### 2. Update Qdrant
```bash
cd ~/qdrant
git pull origin master
CUDA=1 cargo build --release --bin qdrant
sudo systemctl restart qdrant
```

### 3. Backup and Restore
```bash
# Backup Qdrant data
sudo systemctl stop qdrant
tar -czf qdrant-backup-$(date +%Y%m%d).tar.gz ~/qdrant/storage/
sudo systemctl start qdrant

# Restore from backup
sudo systemctl stop qdrant
rm -rf ~/qdrant/storage/*
tar -xzf qdrant-backup-20xxxxxx.tar.gz -C ~/
sudo systemctl start qdrant
```

## Security

### 1. Enable API Key Authentication
Update the configuration file to add API key:

```yaml
# ~/qdrant/config/config.yaml
service:
  host: 0.0.0.0
  http_port: 6333
  grpc_port: 6334
  api_key: "your-secure-api-key-here"  # Add this line
```

Update client code to include API key:

```python
from qdrant_client import QdrantClient

client = QdrantClient(
    host="192.168.1.x",
    port=6333,
    api_key="your-secure-api-key-here"
)
```

### 2. Network Security
- Configure Windows Firewall to allow only the ArXiv Pipeline server to access Qdrant ports
- Consider setting up a VPN if accessing from outside the local network

## Troubleshooting

### 1. GPU Not Detected
- Verify WSL2 NVIDIA drivers: Run `nvidia-smi` in WSL2 terminal
- Ensure CUDA environment variables are set correctly
- Check if the build used CUDA: `ldd ~/qdrant/target/release/qdrant | grep cuda`

### 2. Connection Issues
- Verify the Qdrant service is running: `sudo systemctl status qdrant`
- Check network connectivity: `telnet 192.168.1.x 6333`
- Verify firewall rules are properly set

### 3. Performance Issues
- Monitor GPU memory: `nvidia-smi -l 5`
- Check Qdrant logs for warnings: `journalctl -u qdrant`
- Consider increasing RAM allocation to WSL2:
  ```powershell
  # In PowerShell (Admin) on Windows, create or edit .wslconfig
  notepad "$env:USERPROFILE\.wslconfig"
  
  # Add these lines:
  [wsl2]
  memory=16GB
  processors=8
  ```

---

For more information, visit the [Qdrant Documentation](https://qdrant.tech/documentation/) or the [GitHub Repository](https://github.com/qdrant/qdrant)