import neo4j from 'neo4j-driver';

// Use the Docker service name for Neo4j within the Docker network
// With encrypted:false to avoid certificate issues
const NEO4J_URI = 'bolt://localhost:7687'; // bolt://neo4j:7687
const NEO4J_USER = 'neo4j';
const NEO4J_PASSWORD = 'password';

const driver = neo4j.driver(
  NEO4J_URI,
  neo4j.auth.basic(NEO4J_USER, NEO4J_PASSWORD),
  { encrypted: false } // Disable encryption to avoid certificate issues
);

export const runQuery = async (cypherQuery) => {
  const session = driver.session();
  
  try {
    const result = await session.run(cypherQuery);
    
    // Process the records into a format for Cytoscape
    const nodeMap = new Map();
    const edges = [];
    
    result.records.forEach(record => {
      record.keys.forEach(key => {
        const value = record.get(key);
        
        // Handle nodes
        if (value && value.identity && value.labels) {
          // This is a node
          if (!nodeMap.has(value.identity.toString())) {
            const label = value.properties.name || value.properties.title || value.properties.id || key;
            
            nodeMap.set(value.identity.toString(), {
              data: {
                id: value.identity.toString(),
                label: typeof label === 'string' ? (label.length > 20 ? label.substring(0, 20) + '...' : label) : key,
                type: value.labels[0],
                properties: value.properties
              }
            });
          }
        }
        
        // Handle relationships between nodes
        if (record._fields) {
          for (let i = 0; i < record._fields.length; i++) {
            const field = record._fields[i];
            if (field && field.start && field.end) {
              // This is a relationship
              edges.push({
                data: {
                  id: `${field.start.toString()}-${field.end.toString()}`,
                  source: field.start.toString(),
                  target: field.end.toString(),
                  label: field.type,
                  properties: field.properties
                }
              });
            }
          }
        }
      });
    });
    
    return {
      nodes: Array.from(nodeMap.values()),
      edges
    };
  } catch (error) {
    console.error('Error executing Neo4j query:', error);
    throw error;
  } finally {
    await session.close();
  }
};

export const closeDriver = () => {
  driver.close();
};