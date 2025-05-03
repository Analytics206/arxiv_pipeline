import React, { useState, useEffect } from 'react';
import './App.css';
import queriesConfig from './config/queries';
import GraphVisualization from './components/GraphVisualization';
import { runQuery } from './services/Neo4jService';

function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [queries, setQueries] = useState([]);
  const [selectedQueryId, setSelectedQueryId] = useState('');
  const [graphData, setGraphData] = useState(null);
  const [queryRunning, setQueryRunning] = useState(false);

  useEffect(() => {
    try {
      // Process the imported configuration
      console.log('Loaded config:', queriesConfig);
      
      // Extract queries from the config
      if (queriesConfig && queriesConfig.queries && Array.isArray(queriesConfig.queries)) {
        setQueries(queriesConfig.queries);
        // Set the first query as selected by default
        if (queriesConfig.queries.length > 0) {
          setSelectedQueryId(queriesConfig.queries[0].id);
        }
      } else {
        setQueries([{ id: 'sample', name: 'Sample Query' }]);
        setSelectedQueryId('sample');
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error loading queries:', err);
      setError(err.message);
      setLoading(false);
    }
  }, []);

  const executeQuery = async () => {
    const selectedQuery = queries.find(q => q.id === selectedQueryId);
    if (!selectedQuery) return;
    
    setQueryRunning(true);
    setError(null); // Clear any previous errors
    
    try {
      // Use actual data from Neo4j query
      const data = await runQuery(selectedQuery.cypher);
      setGraphData(data);
    } catch (err) {
      console.error('Error executing query:', err);
      setError(`Error executing query: ${err.message}`);
      // Don't set any mock data on error
      setGraphData(null);
    } finally {
      setQueryRunning(false);
    }
  };

  if (loading) {
    return <div className="App">Loading configuration...</div>;
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>ArXiv Graph Explorer</h1>
        <p>Select and visualize Neo4j graph queries</p>
      </header>
      <main>
        <div className="query-selector">
          <h2>Available Queries</h2>
          <select 
            value={selectedQueryId} 
            onChange={(e) => setSelectedQueryId(e.target.value)}
          >
            {queries.map(q => (
              <option key={q.id} value={q.id}>{q.name}</option>
            ))}
          </select>
          <button 
            className="run-query-button" 
            onClick={executeQuery}
            disabled={queryRunning}
          >
            {queryRunning ? 'Running...' : 'Run Query'}
          </button>
        </div>
        
        {error && (
          <div className="error-message">
            <p>{error}</p>
            <p>Please check your Neo4j connection and try again.</p>
          </div>
        )}
        
        <div className="query-description">
          {queries.length > 0 && (
            <div>
              <h3>Selected Query:</h3>
              {queries.find(q => q.id === selectedQueryId) ? (
                <div>
                  <p><strong>Description:</strong> {queries.find(q => q.id === selectedQueryId).description || 'No description available'}</p>
                  <p><strong>Category:</strong> {queries.find(q => q.id === selectedQueryId).category}</p>
                  <p><strong>Cypher Query:</strong></p>
                  <pre className="cypher-query">{queries.find(q => q.id === selectedQueryId).cypher}</pre>
                </div>
              ) : (
                <p>No query selected</p>
              )}
            </div>
          )}
        </div>
        
        <div className="visualization-container">
          <h2>Graph Visualization</h2>
          {graphData ? (
            <GraphVisualization graphData={graphData} />
          ) : (
            <div className="empty-graph">
              <p>Run a query to visualize the graph</p>
            </div>
          )}
        </div>
      </main>
      <footer className="App-footer">
        <p>ArXiv Pipeline Project - Data Science Tool</p>
      </footer>
    </div>
  );
}

export default App;