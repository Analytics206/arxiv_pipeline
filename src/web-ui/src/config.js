// Configuration settings for the ArXiv Graph Explorer
const config = {
  neo4j: {
    uri: process.env.REACT_APP_NEO4J_URI || 'bolt://localhost:7687',
    user: process.env.REACT_APP_NEO4J_USER || 'neo4j',
    password: process.env.REACT_APP_NEO4J_PASSWORD || 'password',
  },
  // Path to the queries configuration file
  queriesConfigPath: './config/neo4j-queries.yaml'
};

export default config;