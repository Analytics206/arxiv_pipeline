# 📊 External MongoDB Server Setup (Local Network)
- Requirements
    - Docker (on Ubuntu or Docker Desktop on Windows)
    - Git (optional, to clone this repo)

## 🛠 Windows Setup
- Install Docker Desktop from https://www.docker.com/products/docker-desktop.
- Enable "Expose daemon on tcp://localhost:2375 without TLS" (in Docker Desktop → Settings → General).
- Open PowerShell or WSL and navigate to the MongoDB setup directory.
```bash
cd mongodb_setup
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
cd mongodb_setup
docker-compose up --build -d
```

## 🔐 Security Configuration (Optional)

By default, the MongoDB setup runs without authentication for easy development. For production or more secure environments:

1. Edit the `docker-compose.yml` file to uncomment the authentication variables:
```yaml
environment:
  - MONGO_INITDB_ROOT_USERNAME=admin
  - MONGO_INITDB_ROOT_PASSWORD=password
```

2. Change the default credentials to something secure.

3. Restart the container:
```bash
docker-compose down
docker-compose up -d
```

## 🌐 Accessing the MongoDB Server
- Find the IP of the remote machine running MongoDB:
```bash
ip a  # or `ipconfig` on Windows CMD
```
- Then from your local project, connect to:
```python
# Without authentication
mongo_uri = "mongodb://<REMOTE_IP>:27017/"

# With authentication
mongo_uri = "mongodb://admin:password@<REMOTE_IP>:27017/"
```

Update your Python code or .env file:
```python
MONGO_URI=mongodb://<REMOTE_IP>:27017/
```

## 📊 Database Management

### Creating a Database and Collection

```python
import pymongo

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://<REMOTE_IP>:27017/")

# Create or access a database
db = client["arxiv_db"]

# Create or access a collection
papers_collection = db["papers"]

# Insert a document
result = papers_collection.insert_one({"title": "Example Paper", "authors": ["Author 1"]})
print(f"Inserted document ID: {result.inserted_id}")
```

### MongoDB Admin Tools

#### Method 1: Using MongoDB Compass (GUI)
1. Download [MongoDB Compass](https://www.mongodb.com/products/compass)
2. Connect to `mongodb://<REMOTE_IP>:27017/`
3. Manage databases, collections, and documents visually

#### Method 2: Using Docker Exec
```bash
# Connect to MongoDB shell
docker exec -it mongodb-server mongosh

# Basic commands
show dbs
use arxiv_db
show collections
db.papers.find().limit(5)
```

### MongoDB Data Backup and Restore

#### Backup a Database
```bash
# On the host machine
docker exec -it mongodb-server mongodump --db arxiv_db --out /data/backup

# Copy the backup to host
docker cp mongodb-server:/data/backup ./mongodb_backup
```

#### Restore a Database
```bash
# Copy backup to container
docker cp ./mongodb_backup mongodb-server:/data/restore

# Restore from backup
docker exec -it mongodb-server mongorestore --db arxiv_db /data/restore/arxiv_db
```

## ⚙️ Performance Tuning

For optimal performance with the ArXiv pipeline:

1. Create indexes for commonly queried fields:
```javascript
db.papers.createIndex({"paper_id": 1})
db.papers.createIndex({"categories": 1})
db.papers.createIndex({"authors.name": 1})
```

2. Consider using MongoDB Atlas if your data grows beyond what your local server can handle.

## ✅ Verifying It Works
- From your local machine:
```python
import pymongo
try:
    client = pymongo.MongoClient("mongodb://<REMOTE_IP>:27017/", serverSelectionTimeoutMS=2000)
    client.server_info()
    print("MongoDB connection successful!")
    print(f"Available databases: {client.list_database_names()}")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
```

or using curl with the MongoDB REST API (if enabled):
```bash
curl http://<REMOTE_IP>:27017/
```

You should get a response confirming the MongoDB server is running.