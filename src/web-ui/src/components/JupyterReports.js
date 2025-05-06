import React, { useState, useEffect } from 'react';
import { getAllNotebooks, getCategories } from '../services/JupyterService';
import '../styles/JupyterReports.css';

function JupyterReports() {
  const [notebooks, setNotebooks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const notebooksData = await getAllNotebooks();
        const categoriesData = await getCategories();
        
        setNotebooks(notebooksData);
        setCategories(categoriesData);
        setError(null);
      } catch (err) {
        console.error('Error fetching Jupyter notebooks:', err);
        setError('Failed to fetch Jupyter notebooks. Please try again later.');
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  // Filter notebooks based on selected category
  const filteredNotebooks = filter === 'all' 
    ? notebooks 
    : notebooks.filter(notebook => notebook.category === filter);

  return (
    <div className="jupyter-reports-container">
      <header className="jupyter-reports-header">
        <h1>Jupyter Data Analysis Reports</h1>
        <p>Interactive data science notebooks for ArXiv research paper analysis</p>
      </header>

      {loading ? (
        <div className="loading-indicator">Loading Jupyter notebooks...</div>
      ) : error ? (
        <div className="error-message">{error}</div>
      ) : (
        <>
          <div className="category-filter">
            <h2>Categories</h2>
            <div className="filter-buttons">
              <button 
                className={filter === 'all' ? 'active' : ''} 
                onClick={() => setFilter('all')}
              >
                All Reports ({notebooks.length})
              </button>
              {categories.map(category => (
                <button 
                  key={category.name}
                  className={filter === category.name ? 'active' : ''}
                  onClick={() => setFilter(category.name)}
                >
                  {category.displayName} ({category.count})
                </button>
              ))}
            </div>
          </div>

          <div className="notebooks-grid">
            {filteredNotebooks.map(notebook => (
              <div className="notebook-card" key={notebook.id}>
                <div className="notebook-icon">
                  <i className="notebook-icon-jupyter"></i>
                </div>
                <div className="notebook-content">
                  <h3>{notebook.title}</h3>
                  <p>{notebook.description}</p>
                  <div className="notebook-meta">
                    <span className="notebook-date">Last updated: {notebook.lastModified}</span>
                    <span className="notebook-category">{notebook.category}</span>
                  </div>
                </div>
                <div className="notebook-actions">
                  <a 
                    href={`/jupyter/${notebook.filename}`} 
                    className="view-button"
                  >
                    View Report
                  </a>
                  <a 
                    href={`/notebooks/${notebook.filename}`} 
                    className="download-button"
                    download
                  >
                    Download
                  </a>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default JupyterReports;
