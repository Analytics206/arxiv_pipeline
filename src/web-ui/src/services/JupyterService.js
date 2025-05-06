// Service for fetching and handling Jupyter notebooks information

// Mock data based on the notebooks directory
// In a real implementation, this would be fetched from an API
const jupyterNotebooks = [
  {
    id: '01',
    filename: '01_database_connectivity.ipynb',
    title: 'Database Connectivity',
    description: 'Analysis of database connection methods and performance',
    lastModified: '2025-04-28',
    category: 'connectivity'
  },
  {
    id: '02a',
    filename: '02_mongodb_analysis.ipynb',
    title: 'MongoDB Comprehensive Analysis',
    description: 'In-depth analysis of ArXiv data stored in MongoDB',
    lastModified: '2025-04-29',
    category: 'mongodb'
  },
  {
    id: '02b',
    filename: '02_mongodb_analysis_simple.ipynb',
    title: 'MongoDB Simple Analysis',
    description: 'Simplified analysis of ArXiv data for quick insights',
    lastModified: '2025-04-29',
    category: 'mongodb'
  },
  {
    id: '03',
    filename: '03_neo4j_analysis.ipynb',
    title: 'Neo4j Graph Analysis',
    description: 'Graph-based analysis of research paper relationships',
    lastModified: '2025-04-30',
    category: 'neo4j'
  },
  {
    id: '04',
    filename: '04_qdrant_graph_analysis.ipynb',
    title: 'Qdrant Vector Analysis',
    description: 'Semantic search and vector analysis of research papers',
    lastModified: '2025-05-01',
    category: 'qdrant'
  }
];

// Fetch all notebooks
export const getAllNotebooks = async () => {
  // In a real implementation, this would fetch from an API endpoint
  // that reads the notebook directory
  return jupyterNotebooks;
};

// Fetch notebooks by category
export const getNotebooksByCategory = async (category) => {
  // Filter notebooks by category
  return jupyterNotebooks.filter(notebook => notebook.category === category);
};

// Get a notebook by ID
export const getNotebookById = async (id) => {
  // Find a notebook by ID
  return jupyterNotebooks.find(notebook => notebook.id === id);
};

// Get categories with counts
export const getCategories = async () => {
  // Get unique categories
  const categories = [...new Set(jupyterNotebooks.map(notebook => notebook.category))];
  
  // Create category objects with counts
  return categories.map(category => ({
    name: category,
    count: jupyterNotebooks.filter(notebook => notebook.category === category).length,
    displayName: capitalizeFirstLetter(category)
  }));
};

// Helper function to capitalize the first letter
const capitalizeFirstLetter = (string) => {
  return string.charAt(0).toUpperCase() + string.slice(1);
};

// In a real implementation, we would need to add methods to:
// 1. Fetch notebook content from the server
// 2. Execute notebooks and retrieve results
// 3. Save notebook changes
// 4. Export notebooks in various formats
