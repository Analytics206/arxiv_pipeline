import axios from 'axios';
import apiConfig from '../config/api-config';

const NEO4J_API_URL = `${apiConfig.API_BASE_URL}/neo4j`;

// Log API configuration
console.log(`Neo4j API configured with URL: ${NEO4J_API_URL}`);

export const runQuery = async (cypherQuery) => {
  try {
    // Send the Cypher query to the API
    const response = await axios.post(`${NEO4J_API_URL}/run-query`, { cypher_query: cypherQuery });
    
    // The API already processes the results into the correct format for Cytoscape
    return response.data;
  } catch (error) {
    console.error('Error executing Neo4j query via API:', error);
    // Return empty dataset on error to avoid breaking the UI
    return {
      nodes: [],
      edges: [],
      error: error.response?.data?.detail || error.message
    };
  }
};

// Test connection to Neo4j via the API
export const testConnection = async () => {
  try {
    const response = await axios.get(`${NEO4J_API_URL}/test-connection`);
    return response.data;
  } catch (error) {
    console.error('Error testing Neo4j connection:', error);
    return {
      status: 'error',
      message: error.response?.data?.detail || error.message
    };
  }
};

// Get Neo4j database statistics
export const getDBStats = async () => {
  try {
    const response = await axios.get(`${NEO4J_API_URL}/db-stats`);
    return response.data;
  } catch (error) {
    console.error('Error getting Neo4j stats:', error);
    return {
      papers: 0,
      authors: 0,
      categories: 0,
      error: error.response?.data?.detail || error.message
    };
  }
};

// No need to close driver since we're using the API
export const closeDriver = () => {
  // This is now a no-op since we don't have a driver to close
  // Kept for backward compatibility
  console.log('No direct Neo4j connection to close. Using API instead.');
};
