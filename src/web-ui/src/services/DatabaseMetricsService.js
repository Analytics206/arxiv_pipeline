import neo4j from 'neo4j-driver';
import config from '../config';
import apiConfig from '../config/api-config';

// Neo4j metrics queries
const PAPERS_COUNT_QUERY = 'MATCH (p:Paper) RETURN count(p) as count';
const AUTHORS_COUNT_QUERY = 'MATCH (a:Author) RETURN count(a) as count';
const CATEGORIES_COUNT_QUERY = 'MATCH (c:Category) RETURN count(c) as count';

// Initialize driver with connection settings from config
let neo4jDriver = null;

// Function to initialize Neo4j driver
const initNeo4jDriver = () => {
  try {
    if (!neo4jDriver) {
      neo4jDriver = neo4j.driver(
        config.neo4j.uri,
        neo4j.auth.basic(config.neo4j.user, config.neo4j.password),
        { encrypted: false }
      );
      console.log('Neo4j driver initialized with URI:', config.neo4j.uri);
    }
    return neo4jDriver;
  } catch (error) {
    console.error('Failed to initialize Neo4j driver:', error);
    return null;
  }
};

// Check Neo4j connection
export const checkNeo4jConnection = async () => {
  try {
    const driver = initNeo4jDriver();
    if (!driver) return { connected: false };

    const session = driver.session();
    await session.run('RETURN 1');
    await session.close();
    return { connected: true };
  } catch (error) {
    console.error('Neo4j connection check failed:', error);
    return { connected: false };
  }
};

// Get Neo4j metrics
export const getNeo4jMetrics = async () => {
  try {
    const connection = await checkNeo4jConnection();
    if (!connection.connected) {
      return { papers: 0, authors: 0, categories: 0 };
    }

    const driver = neo4jDriver;
    const session = driver.session();

    // Fetch paper count
    const papersResult = await session.run(PAPERS_COUNT_QUERY);
    const papers = papersResult.records[0]?.get('count').toNumber() || 0;

    // Fetch author count
    const authorsResult = await session.run(AUTHORS_COUNT_QUERY);
    const authors = authorsResult.records[0]?.get('count').toNumber() || 0;

    // Fetch category count
    const categoriesResult = await session.run(CATEGORIES_COUNT_QUERY);
    const categories = categoriesResult.records[0]?.get('count').toNumber() || 0;

    await session.close();
    return { papers, authors, categories };
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
  const neo4jConnection = await checkNeo4jConnection();
  const mongoDBConnection = await checkMongoDBConnection();
  const qdrantConnection = await checkQdrantConnection();

  const neo4jMetrics = neo4jConnection.connected ? await getNeo4jMetrics() : { papers: 0, authors: 0, categories: 0 };

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
