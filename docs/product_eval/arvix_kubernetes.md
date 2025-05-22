## 🚢 ArXiv Pipeline on Kubernetes

### Sample Deployment Manifests

```yaml
# mongodb-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mongodb
spec:
  serviceName: mongodb
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
      - name: mongodb
        image: mongo:latest
        ports:
        - containerPort: 27017
        volumeMounts:
        - name: mongodb-data
          mountPath: /data/db
  volumeClaimTemplates:
  - metadata:
      name: mongodb-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

### 2. Resource Recommendations

```markdown
## 💻 Resource Recommendations for ArXiv Pipeline

| Component | CPU Request | Memory Request | CPU Limit | Memory Limit | Notes |
|-----------|-------------|----------------|-----------|--------------|-------|
| MongoDB   | 1           | 2Gi            | 2         | 4Gi          | Storage-heavy workload |
| Neo4j     | 2           | 4Gi            | 4         | 8Gi          | Graph operations need more CPU |
| Qdrant    | 2           | 4Gi            | 4         | 16Gi         | Vector operations memory-intensive |
| Web UI    | 0.5         | 512Mi          | 1         | 1Gi          | Scales horizontally |
| API       | 1           | 1Gi            | 2         | 2Gi          | Connection handling |
```

## 3. 🎮 GPU Resource Management

### NVIDIA GPU Operator
```bash
# Install NVIDIA GPU Operator
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update
helm install gpu-operator nvidia/gpu-operator

# Verify GPU nodes
kubectl get nodes -o wide -l nvidia.com/gpu.present=true
```

### Pod Spec with GPU Request
```bash
apiVersion: v1
kind: Pod
metadata:
  name: vector-processing
spec:
  containers:
  - name: qdrant-gpu
    image: qdrant/qdrant:latest
    resources:
      limits:
        nvidia.com/gpu: 1  # Request 1 GPU
```

### 4. Monitoring Integration


## 📊 Prometheus & Grafana Integration
### Installing Prometheus Operator
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack
```

### ServiceMonitor Example for MongoDB
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: mongodb-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: mongodb
  endpoints:
  - port: metrics
    interval: 30s
```
### Grafana Dashboard Import
```yaml
# Port-forward to Grafana
kubectl port-forward svc/prometheus-grafana 3000:80

# Open browser to http://localhost:3000
# Login with admin/prom-operator
# Import dashboard ID 7362 for MongoDB metrics
```


### 5. Deployment Strategies
## 🔄 Deployment Strategies

### Rolling Updates (Default)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```
```yaml
# Deploy new version (green)
kubectl apply -f api-deployment-v2.yaml

# Verify green deployment is ready
kubectl get pods -l app=api,version=v2

# Switch service to green deployment
kubectl patch service api -p '{"spec":{"selector":{"version":"v2"}}}'
```


### 6. Troubleshooting Section

## 🔍 Troubleshooting ArXiv Pipeline

### Common Issues

#### MongoDB Connection Issues
```bash
# Check if MongoDB pods are running
kubectl get pods -l app=mongodb

# Check logs
kubectl logs -l app=mongodb

# Check if service is correctly configured
kubectl describe service mongodb

# Test connection from another pod
kubectl run mongo-client --rm -it --image=mongo -- mongo mongodb://mongodb:27017
```

### Neo4j Health Check
```yaml 
# Port forward to Neo4j
kubectl port-forward svc/neo4j 7474:7474 7687:7687

# Open browser to http://localhost:7474
```
### Volume Mount Issues
```yaml 
# Check persistent volume claims
kubectl get pvc

# Check persistent volumes
kubectl get pv

# Check storage class
kubectl get storageclass
```


## Additional Resources

Consider adding links to:
1. Kubernetes patterns for microservices
2. Database-specific operator documentation (MongoDB operator, etc.)
3. GitHub repos with example deployments similar to your architecture

By adding these sections, your Kubernetes.md would be not just a general reference, but a specific guide tailored to deploying and operating your ArXiv pipeline on Kubernetes, making it much more valuable as a use case template.## Additional Resources

Consider adding links to:
1. Kubernetes patterns for microservices
2. Database-specific operator documentation (MongoDB operator, etc.)
3. GitHub repos with example deployments similar to your architecture

### By adding these sections, your Kubernetes.md would be not just a general reference, but a specific guide tailored to deploying and operating your ArXiv pipeline on Kubernetes, making it much more valuable as a use case template.

