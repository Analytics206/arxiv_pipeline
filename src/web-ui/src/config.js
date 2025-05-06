// Configuration settings for the ArXiv Pipeline Dashboard
const config = {
  // Neo4j connection settings
  neo4j: {
    uri: process.env.REACT_APP_NEO4J_URI || 'bolt://localhost:7687',
    user: process.env.REACT_APP_NEO4J_USER || 'neo4j',
    password: process.env.REACT_APP_NEO4J_PASSWORD || 'password',
  },
  // MongoDB connection settings
  mongodb: {
    uri: process.env.REACT_APP_MONGODB_URI || 'mongodb://localhost:27017',
    database: process.env.REACT_APP_MONGODB_DB || 'arxiv',
  },
  // Qdrant connection settings
  qdrant: {
    url: process.env.REACT_APP_QDRANT_URL || 'http://localhost:6333',
    collection: process.env.REACT_APP_QDRANT_COLLECTION || 'papers',
  },
  // Path to the queries configuration file
  queriesConfigPath: './config/neo4j-queries.yaml',
  // Default config file path for config editor
  defaultConfigPath: process.env.REACT_APP_DEFAULT_CONFIG_PATH || './config/default.yaml',
  // Pipeline management API endpoint
  pipelineApiUrl: process.env.REACT_APP_PIPELINE_API_URL || 'http://localhost:5000/api'
};

export default config;