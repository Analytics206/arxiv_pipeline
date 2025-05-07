# 🔍 External Neo4j Server Setup (Local Network)
- Requirements
    - Docker (on Ubuntu or Docker Desktop on Windows)
    - Git (optional, to clone this repo)

## 🛠 Windows Setup
- Install Docker Desktop from https://www.docker.com/products/docker-desktop.
- Enable "Expose daemon on tcp://localhost:2375 without TLS" (in Docker Desktop → Settings → General).
- Open PowerShell or WSL and navigate to the Neo4j setup directory.
```bash
cd neo4j_setup
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
cd neo4j_setup
docker-compose up --build -d
```

## 🔐 Security Configuration (Optional)

By default, the Neo4j setup uses the credentials `neo4j/password`. For production or more secure environments:

1. Edit the `docker-compose.yml` file to change the authentication variables:
```yaml
environment:
  - NEO4J_AUTH=neo4j/your_secure_password
```

2. Restart the container:
```bash
docker-compose down
docker-compose up -d
```

## 🌐 Accessing the Neo4j Server

### Browser Interface
- Find the IP of the remote machine running Neo4j:
```bash
ip a  # or `ipconfig` on Windows CMD
```
- Access the Neo4j Browser by navigating to:
```
http://<REMOTE_IP>:7474
```
- Login with the credentials (default: neo4j/password)

### Connect via Bolt Protocol
- Connection URI for your applications:
```
bolt://<REMOTE_IP>:7687
```

Update your Python code or .env file:
```python
NEO4J_URI=bolt://<REMOTE_IP>:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

## 📒 Graph Database Management

### Connecting with Python

```python
from neo4j import GraphDatabase

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record for record in result]

# Example usage
conn = Neo4jConnection(
    uri="bolt://<REMOTE_IP>:7687",
    user="neo4j",
    password="password"
)

# Create a node
query = """
    CREATE (p:Paper {title: $title, id: $id})
    RETURN p
"""
result = conn.run_query(query, {"title": "Example Research Paper", "id": "2305.12345"})
print(f"Created node: {result}")

# Close the connection when done
conn.close()
```

### Schema and Indexes for ArXiv Pipeline

For optimal performance with the ArXiv pipeline, create these indexes and constraints:

```cypher
// Create constraints
CREATE CONSTRAINT paper_id IF NOT EXISTS
FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE;

CREATE CONSTRAINT author_name IF NOT EXISTS
FOR (a:Author) REQUIRE a.name IS UNIQUE;

CREATE CONSTRAINT category_name IF NOT EXISTS
FOR (c:Category) REQUIRE c.name IS UNIQUE;

// Create indexes for common properties
CREATE INDEX paper_title IF NOT EXISTS
FOR (p:Paper) ON (p.title);

CREATE INDEX paper_date IF NOT EXISTS
FOR (p:Paper) ON (p.published_date);
```

### Backup and Restore

#### Backup a Database
```bash
# On the host machine
docker exec -it neo4j-server neo4j-admin dump --database=neo4j --to=/import/neo4j_backup.dump

# Copy the backup to host
docker cp neo4j-server:/import/neo4j_backup.dump ./neo4j_backup.dump
```

#### Restore a Database
```bash
# Copy backup to container
docker cp ./neo4j_backup.dump neo4j-server:/import/

# Stop the database
docker exec -it neo4j-server neo4j stop

# Restore from backup
docker exec -it neo4j-server neo4j-admin load --from=/import/neo4j_backup.dump --database=neo4j --force

# Restart Neo4j
docker exec -it neo4j-server neo4j start
```

## ⚙️ Performance Tuning

For optimal performance with the ArXiv pipeline:

1. Adjust memory settings in `docker-compose.yml` based on your server capacity:
```yaml
environment:
  - NEO4J_dbms_memory_pagecache_size=4G        # Increase for larger graphs
  - NEO4J_dbms_memory_heap_initial__size=2G    # Starting heap size
  - NEO4J_dbms_memory_heap_max__size=4G        # Maximum heap size
```

2. If your graph becomes very large, consider these additional settings:
```yaml
  - NEO4J_dbms_transaction_concurrent_maximum=32  # More concurrent transactions
  - NEO4J_dbms_threads_worker_count=4             # Worker threads (CPU-dependent)
```

## ✅ Verifying It Works

### Python Verification
```python
from neo4j import GraphDatabase

try:
    driver = GraphDatabase.driver(
        "bolt://<REMOTE_IP>:7687", 
        auth=("neo4j", "password")
    )
    with driver.session() as session:
        result = session.run("RETURN 'Neo4j connection successful!' AS message")
        print(result.single()["message"])
    driver.close()
except Exception as e:
    print(f"Neo4j connection failed: {e}")
```

### Browser Verification
Navigate to `http://<REMOTE_IP>:7474` in your web browser. You should see the Neo4j Browser interface, which allows you to run Cypher queries and visualize your graph data.