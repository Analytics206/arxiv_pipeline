# 🧠 External Ollama Server Setup (Local Network)
- Requirements
    - Docker (on Ubuntu or Docker Desktop on Windows)
    - Git (optional, to clone this repo)

## 🛠 Windows Setup
- Install Docker Desktop from https://www.docker.com/products/docker-desktop.
- Enable "Expose daemon on tcp://localhost:2375 without TLS" (in Docker Desktop → Settings → General).
- Open PowerShell or WSL and clone or copy the Ollama server repo.
```bash
git clone https://github.com/your-org/ollama-server
cd ollama-server
```
Run:
```bash
docker-compose up --build -d
```

## 🛠 Ubuntu Setup
```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
git clone https://github.com/your-org/ollama-server
cd ollama-server
docker-compose up --build -d
```

## 🌐 Accessing the Ollama Server
- Find the IP of the remote machine running Ollama:
```bash
ip a  # or `ipconfig` on Windows CMD
```
- Then from your local project, connect to:
```python
ollama_url = "http://<REMOTE_IP>:11434"
```
Update your Python code or .env:
```python
OLLAMA_API=http://<REMOTE_IP>:11434
```

## 📚 Installing & Managing Models

### Installing Models
You can install models in several ways:

#### Method 1: Using the REST API
```bash
# From any machine on your network:

# Install a model - replace 'llama3' with any available model
curl -X POST http://<REMOTE_IP>:11434/api/pull -d '{"name":"llama3"}'

# For a specific model version
curl -X POST http://<REMOTE_IP>:11434/api/pull -d '{"name":"llama3:8b"}'

# For a quantized version (smaller, faster, slightly lower quality)
curl -X POST http://<REMOTE_IP>:11434/api/pull -d '{"name":"llama3:8b-q4_0"}'
```

#### Method 2: Directly via Docker
```bash
# On the machine hosting the Docker container:
docker exec -it ollama-server ollama pull llama3
docker exec -it ollama-server ollama pull mistral
docker exec -it ollama-server ollama pull gemma:7b
```

#### Method 3: From Python
```python
import requests

def install_model(model_name, server_ip):
    url = f"http://{server_ip}:11434/api/pull"
    payload = {"name": model_name}
    response = requests.post(url, json=payload)
    return response.json()

# Example usage
result = install_model("llama3", "<REMOTE_IP>")
print(result)
```

### Listing Available Models
```bash
# Using curl
curl http://<REMOTE_IP>:11434/api/tags

# Or via Docker
docker exec -it ollama-server ollama list
```

### Removing Models
```bash
# Using the API
curl -X DELETE http://<REMOTE_IP>:11434/api/delete -d '{"name":"llama3"}'

# Or via Docker
docker exec -it ollama-server ollama rm llama3
```

### Recommended Models for ArXiv Pipeline
Depending on your use case, these models perform well with academic content:

| Model | Size | Good For | Installation Command |
|-------|------|----------|----------------------|
| llama3 | 8B | General text processing | `ollama pull llama3:8b` |
| llama3 | 70B | Highest quality responses | `ollama pull llama3:70b` |
| mixtral | 8x7B | Excellent on academic text | `ollama pull mixtral` |
| phi3 | 14B | Academic summaries | `ollama pull phi3:14b` |

### Model Disk Space Requirements
Be aware of disk space requirements before installing models:

| Model Size | Typical Disk Space | RAM Recommended |
|------------|-------------------|------------------|
| 7-8B | 4-6 GB | 8-16 GB |
| 13-14B | 7-10 GB | 16-24 GB |
| 70B | 40-45 GB | 80+ GB |

## ✅ Verifying It Works
- From your local machine:
```python
import requests
response = requests.get("http://<REMOTE_IP>:11434/health")
print(response.json())
```
or 
```bash
curl http://<REMOTE_IP>:11434/api/tags
```
- You should get a JSON response with available models.
