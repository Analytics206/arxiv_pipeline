import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import '../styles/Home.css';
import { getAllDatabaseMetrics } from '../services/DatabaseMetricsService';

function Home() {
  // State for database metrics and loading status
  const [metrics, setMetrics] = useState({
    neo4j: { connected: false, metrics: { papers: 0, authors: 0, categories: 0 } },
    mongodb: { connected: false, metrics: { papers: 0, authors: 0, categories: 0 } },
    qdrant: { connected: false, metrics: { papers: 0, authors: 0, categories: 0 } }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Format large numbers with commas
  const formatNumber = (num) => {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  };

  // Fetch database metrics when component mounts
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const data = await getAllDatabaseMetrics();
        setMetrics(data);
        setError(null);
      } catch (err) {
        console.error('Error fetching database metrics:', err);
        setError('Failed to fetch database metrics. Please check your connections.');
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();

    // Set up polling interval (every 30 seconds)
    const intervalId = setInterval(fetchMetrics, 30000);

    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="home-container">
      <h1 className="main-title">Deep Research Pipeline Dashboard</h1>
      <p className="subtitle">AI Research Papers Analytics Platform</p>
      
      <div className="cards-container">
        <div className="card">
          <h2>Neo4j Explorer</h2>
          <p>Visualize and explore research papers as a knowledge graph</p>
          <p>Connect to Neo4j database to query and visualize paper relationships</p>
          <Link to="/neo4j" className="card-button">Launch</Link>
        </div>
        
        <div className="card">
          <h2>MongoDB Reports</h2>
          <p>Access and create customized reports from paper metadata</p>
          <p>Run custom queries and generate visualizations from MongoDB data</p>
          <Link to="/mongodb" className="card-button">Launch</Link>
        </div>
        
        <div className="card">
          <h2>Qdrant Search</h2>
          <p>Perform semantic search across research papers</p>
          <p>Find relevant papers using vector similarity search</p>
          <Link to="/qdrant" className="card-button">Launch</Link>
        </div>
        
        <div className="card">
          <h2>Jupyter Reports</h2>
          <p>Access data analysis notebooks and reports</p>
          <p>View and download interactive Jupyter notebooks with research insights</p>
          <Link to="/jupyter" className="card-button">Launch</Link>
        </div>
        
        <div className="card">
          <h2>Config Editor</h2>
          <p>Edit and save application configuration</p>
          <p>Modify the default.yaml settings for all pipeline components</p>
          <Link to="/config" className="card-button">Launch</Link>
        </div>
        
        <div className="card">
          <h2>Pipeline Management</h2>
          <p>Start, stop and monitor data pipelines</p>
          <p>Control and monitor the status of all data processing jobs</p>
          <Link to="/pipelines" className="card-button">Launch</Link>
        </div>
      </div>
      
      <div className="metrics-table-container">
        <h2 className="metrics-title">Database Metrics</h2>
        {loading ? (
          <div className="loading-indicator">Loading database metrics...</div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : (
          <table className="metrics-table">
            <thead>
              <tr>
                <th>Database</th>
                <th>Connection Status</th>
                <th>Papers</th>
                <th>Authors</th>
                <th>Categories</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Neo4j</td>
                <td className={metrics.neo4j.connected ? "status-connected" : "status-disconnected"}>
                  {metrics.neo4j.connected ? "Connected" : "Disconnected"}
                </td>
                <td>{formatNumber(metrics.neo4j.metrics.papers)}</td>
                <td>{formatNumber(metrics.neo4j.metrics.authors)}</td>
                <td>{formatNumber(metrics.neo4j.metrics.categories)}</td>
              </tr>
              <tr>
                <td>MongoDB</td>
                <td className={metrics.mongodb.connected ? "status-connected" : "status-disconnected"}>
                  {metrics.mongodb.connected ? "Connected" : "Disconnected"}
                </td>
                <td>{formatNumber(metrics.mongodb.metrics.papers)}</td>
                <td>{formatNumber(metrics.mongodb.metrics.authors)}</td>
                <td>{formatNumber(metrics.mongodb.metrics.categories)}</td>
              </tr>
              <tr>
                <td>Qdrant</td>
                <td className={metrics.qdrant.connected ? "status-connected" : "status-disconnected"}>
                  {metrics.qdrant.connected ? "Connected" : "Disconnected"}
                </td>
                <td>{formatNumber(metrics.qdrant.metrics.papers)}</td>
                <td>{formatNumber(metrics.qdrant.metrics.authors)}</td>
                <td>{formatNumber(metrics.qdrant.metrics.categories)}</td>
              </tr>
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default Home;
