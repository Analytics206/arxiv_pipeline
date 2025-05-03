
# 📗 Product Requirements Document (PRD)

## Functional Requirements

### 3.0 Dockerization (FR-DCK)
- **FR-DCK-01**: System shall provide Dockerfiles for each service (ingestion, db, embedding, etc.)
- **FR-DCK-02**: System shall include a `docker-compose.yml` file to orchestrate local setup
- **FR-DCK-03**: Docker containers shall support volume mounting for persistent local data

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

### 3.3 Graph Database (Neo4j) (FR-GPH)
- **FR-GPH-01**: Convert MongoDB data into Neo4j nodes/relationships
- **FR-GPH-02**: Represent papers with properties (title, abstract, date)
- **FR-GPH-03**: Represent authors and categories as nodes
- **FR-GPH-04**: Create (:Author)-[:AUTHORED]->(:Paper)
- **FR-GPH-05**: Create (:Paper)-[:BELONGS_TO]->(:Category)

### 3.4 Vector Embeddings (Qdrant) (FR-VEC)
- **FR-VEC-01**: Use Hugging Face embedding models
- **FR-VEC-02**: Embed title + abstract as text input
- **FR-VEC-03**: Store vectors and metadata in Qdrant
- **FR-VEC-04**: Allow embedding model switching via config

### 3.5 Configuration & Modularity (FR-CON)
- **FR-CON-01**: Centralized settings file
- **FR-CON-02**: Modular execution of pipeline components
- **FR-CON-03**: Optional CLI or orchestrator support

### 3.6 Logging & Monitoring (FR-LOG)
- **FR-LOG-01**: Log ingestion/storage/indexing steps
- **FR-LOG-02**: Log network and processing errors
- **FR-LOG-03**: Log reasons for skipped entries

### 3.7 Web UI (FR-UI-01)
- **FR-UI-01**: Web UI to explore neo4j graph/search
- **FR-UI-02**: Extend to MongoDB
- **FR-UI-03**: Extend to Qdrant

### Optional/Nice-to-Have Features
- **FR-PDF-01**: Optional PDF downloading/section parsing
- **FR-REF-01**: Parse citation relationships
- **FR-CRON-01**: Schedule periodic updates
- **FR-REP-01**: Provide sample notebooks for usage

