import config from '../config';
import apiConfig from '../config/api-config';
import axios from 'axios';

// API configuration for Neo4j
const NEO4J_API_URL = `${apiConfig.API_BASE_URL}/neo4j`;

// Check Neo4j connection through API
export const checkNeo4jConnection = async () => {
  try {
    console.log(`Checking Neo4j connection via API: ${NEO4J_API_URL}/test-connection`);
    const response = await axios.get(`${NEO4J_API_URL}/test-connection`);
    
    return { 
      connected: response.data.status === 'success',
      databases: response.data.databases || [] 
    };
  } catch (error) {
    console.error('Neo4j connection check failed:', error);
    return { connected: false };
  }
};

// Get Neo4j metrics via API
export const getNeo4jMetrics = async () => {
  try {
    console.log(`Fetching Neo4j metrics from API: ${NEO4J_API_URL}/db-stats`);
    const response = await axios.get(`${NEO4J_API_URL}/db-stats`);
    
    return {
      papers: response.data.papers || 0,
      authors: response.data.authors || 0,
      categories: response.data.categories || 0
    };
  } catch (error) {
    console.error('Failed to get Neo4j metrics:', error);
    return { papers: 0, authors: 0, categories: 0 };
  }
};

// Check MongoDB connection and get metrics from FastAPI
export const checkMongoDBConnection = async () => {
  try {
    const response = await fetch(`${apiConfig.API_BASE_URL}/metrics/mongodb/test-connection`);
    if (!response.ok) throw new Error('MongoDB API not reachable');
    const data = await response.json();
    return {
      connected: data.status === 'success',
      databases: data.databases || [],
    };
  } catch (error) {
    console.error('MongoDB connection check failed:', error);
    return { connected: false, databases: [] };
  }
};

// Check Qdrant connection
export const checkQdrantConnection = async () => {
  try {
    console.log(`Attempting to connect to Qdrant API at: ${apiConfig.API_BASE_URL}/metrics/qdrant/test-connection`);
    const response = await fetch(`${apiConfig.API_BASE_URL}/metrics/qdrant/test-connection`);
    
    if (!response.ok) {
      console.error(`Qdrant API not reachable. Status: ${response.status}, StatusText: ${response.statusText}`);
      return { connected: false, error: `API Error: ${response.status} ${response.statusText}` };
    }
    
    const data = await response.json();
    console.log('Qdrant connection response:', data);
    
    // Return connected true only if status is success
    const isConnected = data.status === 'success';
    return { 
      connected: isConnected,
      message: data.message || '',
      status: data.status || 'unknown'
    };
  } catch (error) {
    console.error('Qdrant connection check failed:', error);
    return { connected: false, error: error.message };
  }
};

// Get Qdrant metrics
export const getQdrantMetrics = async (isConnected) => {
  if (!isConnected) {
    console.log('Skipping Qdrant metrics fetch - not connected');
    return { papers: 0, authors: 0, categories: 0 };
  }
  
  try {
    console.log(`Fetching Qdrant metrics from: ${apiConfig.API_BASE_URL}/metrics/qdrant/paper-stats`);
    const response = await fetch(`${apiConfig.API_BASE_URL}/metrics/qdrant/paper-stats`);
    
    if (!response.ok) {
      console.error(`Failed to fetch Qdrant metrics. Status: ${response.status}, StatusText: ${response.statusText}`);
      return { papers: 0, authors: 0, categories: 0 };
    }
    
    const stats = await response.json();
    console.log('Received Qdrant metrics:', stats);
    
    return {
      papers: stats.papers || 0,
      authors: stats.authors || 0,
      categories: stats.categories || 0
    };
  } catch (error) {
    console.error('Failed to fetch Qdrant metrics:', error);
    return { papers: 0, authors: 0, categories: 0 };
  }
};

// Get papers analysis by year/month/day
export const getPaperAnalysisByTime = async (startDate = null, endDate = null, yearFilter = null, category = null) => {
  try {
    // Build the query parameters
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (yearFilter) params.append('year_filter', yearFilter);
    if (category) params.append('category', category);
    
    const queryString = params.toString() ? `?${params.toString()}` : '';
    
    console.log(`Fetching paper analysis data from: ${apiConfig.API_BASE_URL}/metrics/mongodb/paper-analysis${queryString}`);
    const response = await fetch(`${apiConfig.API_BASE_URL}/metrics/mongodb/paper-analysis${queryString}`);
    
    if (!response.ok) {
      console.error(`Failed to fetch paper analysis data. Status: ${response.status}`);
      return { yearly: {}, monthly: {}, daily: {}, total_papers: 0 };
    }
    
    const data = await response.json();
    console.log('Received paper analysis data:', data);
    
    return data;
  } catch (error) {
    console.error('Failed to fetch paper analysis data:', error);
    return { yearly: {}, monthly: {}, daily: {}, total_papers: 0 };
  }
};

// Get all database metrics
export const getAllDatabaseMetrics = async () => {
  // All connections are checked via API
  const mongoDBConnection = await checkMongoDBConnection();
  const qdrantConnection = await checkQdrantConnection();
  const neo4jConnection = await checkNeo4jConnection();
  
  // Always get Neo4j metrics through API regardless of connection status
  // The API will return zeros if there's an issue
  const neo4jMetrics = await getNeo4jMetrics();

  // For MongoDB: count documents in the arxiv_papers.papers collection if connected
  let mongoMetrics = { papers: 0, authors: 0, categories: 0 };
  if (mongoDBConnection.connected && mongoDBConnection.databases.includes('arxiv_papers')) {
    try {
      // Fetch papers count from a new API endpoint (to be implemented)
      const response = await fetch(`${apiConfig.API_BASE_URL}/metrics/mongodb/paper-stats`);
      if (response.ok) {
        const stats = await response.json();
        mongoMetrics = {
          papers: stats.papers || 0,
          authors: stats.authors || 0,
          categories: stats.categories || 0,
        };
      }
    } catch (err) {
      console.error('Failed to fetch MongoDB metrics:', err);
    }
  }

  return {
    neo4j: {
      connected: neo4jConnection.connected,
      metrics: neo4jMetrics
    },
    mongodb: {
      connected: mongoDBConnection.connected,
      metrics: mongoMetrics
    },
    qdrant: {
      connected: qdrantConnection.connected,
      metrics: await getQdrantMetrics(qdrantConnection.connected)
    }
  };
};
