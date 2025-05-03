/**
 * Transforms Neo4j data into Cytoscape.js compatible format
 * @param {Object} neo4jData - Data returned from Neo4jService
 * @param {Object} options - Visualization options
 * @returns {Object} - Cytoscape elements object with nodes and edges
 */
export const transformNeo4jDataToCytoscape = (neo4jData, options = {}) => {
  const { nodes, relationships } = neo4jData;
  const nodeColorMap = options?.node_color_map || {};
  const nodeSizeProperty = options?.node_size_property;
  
  // Transform nodes
  const cytoscapeNodes = nodes.map(node => {
    // Determine node color based on node type
    const color = nodeColorMap[node.type] || '#666';
    
    // Determine node size based on specified property
    let size = 30; // default size
    if (nodeSizeProperty && node.properties[nodeSizeProperty]) {
      // Scale size based on property value (between 20 and 60)
      const value = node.properties[nodeSizeProperty];
      size = typeof value === 'number' ? Math.max(20, Math.min(60, 20 + value * 2)) : 30;
    }
    
    // Create label from node properties
    let label = '';
    if (node.type === 'Paper') {
      // For papers, use truncated title
      label = truncateString(node.properties.title || 'Untitled', 30);
    } else if (node.type === 'Author') {
      // For authors, use name
      label = node.properties.name || 'Unknown';
    } else if (node.type === 'Category') {
      // For categories, use code
      label = node.properties.code || node.properties.term || 'Unknown';
    } else {
      // Default label is first available property
      const firstProp = Object.values(node.properties)[0];
      label = firstProp ? truncateString(firstProp.toString(), 20) : 'Node';
    }
    
    return {
      data: {
        id: node.id,
        label,
        type: node.type,
        properties: node.properties,
        size
      },
      style: {
        'background-color': color,
        'width': size,
        'height': size
      }
    };
  });
  
  // Transform relationships
  const cytoscapeEdges = relationships.map(rel => {
    return {
      data: {
        id: rel.id,
        source: rel.startNodeId,
        target: rel.endNodeId,
        label: rel.type.replace('_', ' '),
        type: rel.type,
        properties: rel.properties
      }
    };
  });
  
  return {
    nodes: cytoscapeNodes,
    edges: cytoscapeEdges
  };
};

/**
 * Helper function to truncate strings
 * @param {string} str - String to truncate
 * @param {number} length - Maximum length
 * @returns {string} - Truncated string
 */
const truncateString = (str, length) => {
  if (!str) return '';
  return str.length > length ? str.substring(0, length) + '...' : str;
};
