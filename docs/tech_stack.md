# 🛠️ Technical Stack Documentation

## System Architecture Overview

The ArXiv Research Pipeline is built on a microservices architecture using Docker containers with the following components:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Ingestion     │────▶│  Data Storage   │────▶│   Processing    │
│   Service       │     │    Layer        │     │    Layer        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│      User       │◀────│   Knowledge     │◀────│   Vector        │
│   Interface     │     │     Graph       │     │   Embeddings    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Core Technologies

### Infrastructure & Containerization
- **Docker**: All services containerized for isolation and portability
- **Docker Compose**: Multi-container orchestration for local development
- **Python 3.12**: Core programming language (slim container variant)
- **UV Package Manager**: Fast Python dependency management
- **Git**: Version control system

### Ingestion Layer
- **ArXiv API**: HTTP-based Atom XML API for research paper retrieval
- **Requests**: HTTP client library
- **ElementTree**: XML parsing for ArXiv response data
- **Rate limiting**: Configurable throttling to respect API constraints

### Data Storage Layer
- **MongoDB**: NoSQL document database for paper metadata storage
  - Collections: papers, authors, categories
  - Indexes for efficient querying
- **Docker volumes**: Persistent storage for database contents

### Graph Representation
- **Neo4j**: Graph database for representing paper-author-category relationships
  - Nodes: Papers, Authors, Categories 
  - Relationships: AUTHORED, BELONGS_TO
  - Cypher query language
- **Neo4j Python Driver**: Interface for graph operations

### Vector Embeddings
- **Hugging Face Transformers**: Machine learning models for text embeddings
- **Qdrant**: Vector database for similarity search
  - Collections: paper_embeddings
  - Storage of metadata with vectors
- **Embedding models**: Sentence transformers for semantic representation

### PDF Processing
- **PDF Download**: Direct file retrieval from ArXiv
- **Storage**: Local filesystem storage (E:\AI Research)

### Configuration & Utilities
- **YAML**: Configuration file format
- **Environment Variables**: Runtime configuration
- **Logging**: Standard Python logging

## API Integrations
- **ArXiv.org API**: `http://export.arxiv.org/api/query`
  - Categories: cs.AI, cs.LG, cs.CV, etc.
  - Sort options: submittedDate
  - Result limits: Configurable

## Development Tools
- **Python Virtual Environment**: Isolated dependency management
- **Docker Compose**: Local environment orchestration

## Deployment Architecture
```
┌─────────────────────────────────────────────────────────┐
│                     Docker Environment                   │
│                                                          │
│   ┌─────────┐     ┌──────────┐     ┌────────────┐       │
│   │  app    │────▶│ mongodb  │────▶│ sync-neo4j │       │
│   │         │     │          │     │            │       │
│   └─────────┘     └──────────┘     └────────────┘       │
│        │                │                 │              │
│        ▼                ▼                 ▼              │
│   ┌─────────┐     ┌──────────┐     ┌────────────┐       │
│   │ qdrant  │◀────│  neo4j   │◀────│web-interface│       │
│   │         │     │          │     │            │       │
│   └─────────┘     └──────────┘     └────────────┘       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

### MongoDB Collections
- **papers**: Research paper metadata
  - id: ArXiv ID
  - title: Paper title
  - summary: Abstract
  - authors: Array of author names
  - categories: Array of category codes
  - published: Publication date
  - pdf_url: URL to PDF file
  - vector_id: Reference to vector embedding (if processed)

### Neo4j Graph Model
- **Nodes**:
  - :Paper (id, title, summary, published, pdf_url)
  - :Author (name)
  - :Category (code, description)
- **Relationships**:
  - (:Author)-[:AUTHORED]->(:Paper)
  - (:Paper)-[:BELONGS_TO]->(:Category)

### Qdrant Collections
- **paper_embeddings**:
  - Vector dimension: Model-dependent
  - Metadata: paper_id, title
  - Distance metric: Cosine similarity

## Security Considerations
- Local-first architecture minimizes external dependencies
- Docker isolation for service components
- No exposed credentials in code

## Scaling Considerations
- Container-based architecture supports horizontal scaling
- Database services can be scaled independently
- Modular components allow selective enhancement
