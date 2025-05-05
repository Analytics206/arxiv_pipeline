# Qdrant GPU Setup for ArXiv Pipeline

This guide provides instructions for setting up Qdrant with GPU support on a separate machine within the same network as the ArXiv Pipeline system. This setup enhances vector search performance using GPU acceleration through WSL2 and direct Rust compilation.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Integration with ArXiv Pipeline](#integration-with-arxiv-pipeline)
- [Testing](#testing)
- [Maintenance](#maintenance)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Windows 11** with:
  - [WSL2 enabled](https://learn.microsoft.com/en-us/windows/wsl/install)
  - NVIDIA GPU driver for WSL2 ([Download](https://developer.nvidia.com/cuda/wsl))
- **Minimum Hardware**:
  - 16GB RAM (32GB recommended)
  - NVIDIA GPU with CUDA 12.x support (8GB VRAM minimum)
  - SSD storage (at least 100GB free space)
- **Network**:
  - Static IP on the local network
  - Open ports 6333, 6334 for Qdrant communication
- **Required Software**:
  - Rust and Cargo
  - Python 3.8+ with pip

---

## Installation

### 1. Set Up WSL2
```powershell
# In PowerShell (Admin):
wsl --install -d Ubuntu
wsl --set-version Ubuntu 2
```

### 2. Install CUDA in WSL2
```bash
# Inside Ubuntu WSL:
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-wsl-ubuntu.pin
sudo mv cuda-wsl-ubuntu.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/3bf863cc.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/ /"
sudo apt update
sudo apt -y install cuda
```

### 3. Install Rust and Build Tools
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install build essentials
sudo apt update
sudo apt install -y build-essential pkg-config libssl-dev clang
```

### 4. Build Qdrant with GPU Support
```bash
# Clone Qdrant repository
git clone https://github.com/qdrant/qdrant.git
cd qdrant

# Build with CUDA support
CUDA=1 cargo build --release --bin qdrant

# Verify the build completed successfully
ls -la target/release/qdrant
```

## Configuration

### 1. Create Qdrant Configuration
```bash
# Create directory for configuration
mkdir -p ~/qdrant/config
mkdir -p ~/qdrant/storage

# Create configuration file
cat << EOF > ~/qdrant/config/config.yaml
log_level: INFO

storage:
  storage_path: /home/$(whoami)/qdrant/storage

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

### 2. Create Systemd Service
Create a systemd service file to run Qdrant as a background service:

```bash
sudo tee /etc/systemd/system/qdrant.service > /dev/null << EOF
[Unit]
Description=Qdrant Vector Search Engine with GPU Support
After=network.target

[Service]
ExecStart=/home/$(whoami)/qdrant/target/release/qdrant --config /home/$(whoami)/qdrant/config/config.yaml
Restart=always
User=$(whoami)
Environment="RUST_LOG=info"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable qdrant
sudo systemctl start qdrant

# Check service status
sudo systemctl status qdrant
```

### 3. Open Firewall Ports
```powershell
# In PowerShell (Admin) on Windows:
New-NetFirewallRule -DisplayName "Qdrant HTTP API" -Direction Inbound -LocalPort 6333 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Qdrant gRPC API" -Direction Inbound -LocalPort 6334 -Protocol TCP -Action Allow
```

## Integration with ArXiv Pipeline

### 1. Install Python Client
```bash
# In your ArXiv Pipeline Python environment
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
```python
# create_collection.py
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Replace with your Qdrant server's IP address
QDRANT_HOST = "192.168.1.x"
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

## Testing

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