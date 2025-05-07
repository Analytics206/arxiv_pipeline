import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/NavBar.css';

function NavBar() {
  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <Link to="/">ArXiv Pipeline</Link>
      </div>
      <div className="navbar-links">
        <Link to="/" className="nav-link">Home</Link>
        <Link to="/neo4j" className="nav-link">Neo4j Explorer</Link>
        <Link to="/mongodb" className="nav-link">MongoDB Reports</Link>
        <Link to="/qdrant" className="nav-link">Qdrant Search</Link>
        <Link to="/jupyter" className="nav-link">Jupyter Reports</Link>
        <Link to="/config" className="nav-link">Config Editor</Link>
        <Link to="/pipelines" className="nav-link">Pipeline Management</Link>
        <a href="http://localhost:8000/docs#" className="nav-link" target="_blank" rel="noopener noreferrer">Pipeline API</a>
      </div>
    </nav>
  );
}

export default NavBar;
