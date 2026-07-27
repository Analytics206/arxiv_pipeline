import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/NavBar.css';
import ThemeToggle from './ThemeToggle';
import { apiConfig } from '../services/ResearchService';

function NavBar() {
  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <Link to="/">
          <img src="/images/drp_logo_blue.png" alt="Research Intelligence Home" className="navbar-logo-img" />
          <span>Research Intelligence</span>
        </Link>
      </div>
      <div className="navbar-links">
        <Link to="/research" className="nav-link">Research Search</Link>
        <Link to="/mongodb" className="nav-link">Metadata</Link>
        <a href={`${apiConfig.API_BASE_URL}/docs`} className="nav-link" target="_blank" rel="noopener noreferrer">Agent API</a>
        <ThemeToggle />
      </div>
    </nav>
  );
}

export default NavBar;
