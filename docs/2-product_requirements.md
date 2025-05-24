
# 📗 Product Requirements Document (PRD)

## Functional Requirements

### 3.0 Dockerization (FR-DCK)
- **FR-DCK-01**: System shall provide Dockerfiles for each service (ingestion, db, embedding, etc.)
- **FR-DCK-02**: System shall include a `docker-compose.yml` file to orchestrate local setup
- **FR-DCK-03**: Docker containers shall support volume mounting for persistent local data
- **FR-DCK-04**: System shall provide standalone Docker configurations for external deployment of key services
- **FR-DCK-05**: External Docker configurations shall be independent of the main pipeline and require no other components
- **FR-DCK-06**: External Docker configurations shall include detailed setup documentation

### 3.1 Ingestion (FR-ING)
- **FR-ING-01**: Support fetching metadata from arXiv Atom XML API
- **FR-ING-02**: Support configurable category-based querying (initial: cs.AI)
- **FR-ING-03**: Support configurable result limits
- **FR-ING-04**: Enable category switching via config

### 3.2 Data Management (FR-DAT)
- **FR-DAT-01**: Store raw and normalized metadata in MongoDB
- **FR-DAT-02**: Allow retrieval/inspection of MongoDB documents
- **FR-DAT-03**: Modular MongoDB interface for reuse
- **FR-DAT-04**: Log ingestion statistics and anomalies

### 3.3 LLM Evaluation Framework (FR-LLM)
- **FR-LLM-01**: System shall provide tools for evaluating LLM performance using standard metrics (BLEU, ROUGE, etc.)
- **FR-LLM-02**: Support for multiple model comparison in a single evaluation run
- **FR-LLM-03**: Configurable test datasets for evaluation
- **FR-LLM-04**: Generate comprehensive evaluation reports with metrics and comparisons

### 3.4 Graph Database (Neo4j) (FR-GPH)
- **FR-GPH-01**: Convert MongoDB data into Neo4j nodes/relationships
- **FR-GPH-02**: Represent papers with properties (title, abstract, date)
- **FR-GPH-03**: Represent authors and categories as nodes
- **FR-GPH-04**: Create (:Author)-[:AUTHORED]->(:Paper)
- **FR-GPH-05**: Create (:Paper)-[:BELONGS_TO]->(:Category)

### 3.5 Vector Embeddings (Qdrant) (FR-VEC)
- **FR-VEC-01**: Use Hugging Face embedding models
- **FR-VEC-02**: Embed title + abstract as text input
- **FR-VEC-03**: Store vectors and metadata in Qdrant
- **FR-VEC-04**: Allow embedding model switching via config
- **FR-VEC-05**: Support GPU acceleration for vector operations
- **FR-VEC-06**: Enable deployment on remote dedicated hardware
- **FR-VEC-07**: Provide optimized configuration for research paper embeddings

### 3.6 Configuration & Modularity (FR-CON)
- **FR-CON-01**: Centralized settings file
- **FR-CON-02**: Modular execution of pipeline components
- **FR-CON-03**: Optional CLI or orchestrator support

### 3.7 Logging & Monitoring (FR-LOG)
- **FR-LOG-01**: Log ingestion/storage/indexing steps
- **FR-LOG-02**: Log network and processing errors
- **FR-LOG-03**: Log reasons for skipped entries

### 3.8 System Monitoring (FR-MON)
- **FR-MON-01**: Collect container metrics with Prometheus
- **FR-MON-02**: Collect system metrics with Node Exporter
- **FR-MON-03**: Monitor MongoDB performance with MongoDB Exporter
- **FR-MON-04**: Visualize metrics with Grafana dashboards
- **FR-MON-05**: Support custom application metrics for pipeline operations

### 3.9 Web UI (FR-UI)
- **FR-UI-01**: ✅ Web UI to explore neo4j graph/search
- **FR-UI-02**: Web UI to start/stop pipelines, view logs, and monitor database status
- **FR-UI-03**: Web UI to manage configurations for pipelines
- **FR-UI-04**: 🔄 Extend to MongoDB (Planned for next release)
- **FR-UI-05**: 🔄 Extend to Qdrant (Planned for next release)

### 3.10 Jupyter Notebooks (FR-REP)
- **FR-REP-01**: ✅ Provide sample notebooks for general usage and exploration (Now required for all database interactions)
- **FR-REP-02**: Create connectivity testing notebooks for all databases (MongoDB, Neo4j, Qdrant)
- **FR-REP-03**: Include data visualization capabilities in notebooks
- **FR-REP-04**: Document notebook usage and setup instructions

### 3.11 AI Agent Platform (FR-AGT)
- **FR-AGT-01**: 🔧 Configurable AI Agent platform for research paper analysis and exploration (High priority for next release)

### 3.12 Data Validation and Analysis (FR-VAL)
- **FR-VAL-01**: Interactive dashboards for validating data loaded across different systems
- **FR-VAL-02**: Temporal analysis of paper publications by year, month, and day
- **FR-VAL-03**: Multi-dimensional filtering for data validation (date range, year, category)
- **FR-VAL-04**: Visualization of data integrity and completeness metrics

### 3.13 Event Streaming with Kafka (FR-KAF)
- **FR-KAF-01**: Implement Kafka as a message broker for event-driven architecture
- **FR-KAF-02**: Create event producers for paper ingestion and processing events
- **FR-KAF-03**: Implement event consumers for Neo4j and Qdrant updates
- **FR-KAF-04**: Support event replay for recovery and debugging
- **FR-KAF-05**: Implement dead letter queue for failed message processing
- **FR-KAF-06**: Monitor Kafka cluster health and performance metrics

### 3.15 Data Governance (FR-DGV)
- **FR-DGV-01**: Implement data retention policies for all stored data
- **FR-DGV-02**: Ensure GDPR compliance for author and user data
- **FR-DGV-03**: Implement data quality validation rules and monitoring
- **FR-DGV-04**: Document schema evolution and versioning strategy
- **FR-DGV-05**: Implement data access logging and audit trails

### 3.16 Security Requirements (FR-SEC)
- **FR-SEC-01**: Implement OAuth2/JWT authentication for all API endpoints
- **FR-SEC-02**: Role-based access control (RBAC) for system operations
- **FR-SEC-03**: API rate limiting and abuse prevention mechanisms
- **FR-SEC-04**: Network security controls between services (TLS, mTLS)
- **FR-SEC-05**: Secure secrets management using HashiCorp Vault or similar
- **FR-SEC-06**: Container security scanning in CI/CD pipeline
- **FR-SEC-07**: Regular security audits and penetration testing

### 3.17 Performance Requirements (FR-PER)
- **FR-PER-01**: API response time < 500ms for 95% of requests
- **FR-PER-02**: Support for 100 concurrent users with minimal performance degradation
- **FR-PER-03**: Process 1000+ papers per hour during batch operations
- **FR-PER-04**: Vector search response time < 1 second for 95% of queries
- **FR-PER-05**: Support horizontal scaling of stateless services
- **FR-PER-06**: Implement caching for frequently accessed data (Redis)
- **FR-PER-07**: Database query optimization for common access patterns
- **FR-PER-08**: Asynchronous processing for long-running operations

### 3.14 Advanced Analytics (FR-ANL)
- **FR-ANL-01**: Category-based publication trend analysis with interactive filtering
- **FR-ANL-02**: Visual representation of publication volume across time dimensions

### Optional/Nice-to-Have Features
- **FR-PDF-01**: Optional PDF downloading/section parsing
- **FR-REF-01**: Parse citation relationships
- **FR-CRON-01**: Schedule periodic updates

