import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import '../styles/JupyterViewer.css';

function JupyterViewer() {
  const { notebookId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notebook, setNotebook] = useState(null);

  useEffect(() => {
    // This would be replaced with an actual API call to fetch notebook content
    const fetchNotebook = async () => {
      try {
        setLoading(true);
        
        // For now, we'll just show metadata about the requested notebook
        // In a real implementation, this would fetch the actual notebook content
        const notebookData = {
          id: notebookId,
          title: notebookId.replace('.ipynb', '').replace(/_/g, ' '),
          lastModified: '2025-05-01'
        };
        
        setNotebook(notebookData);
        setError(null);
      } catch (err) {
        console.error('Error fetching notebook:', err);
        setError(`Failed to load notebook: ${notebookId}`);
      } finally {
        setLoading(false);
      }
    };

    fetchNotebook();
  }, [notebookId]);

  if (loading) {
    return <div className="jupyter-viewer-container loading">Loading notebook...</div>;
  }

  if (error) {
    return (
      <div className="jupyter-viewer-container error">
        <div className="error-message">{error}</div>
        <Link to="/jupyter" className="back-button">Back to Reports</Link>
      </div>
    );
  }

  return (
    <div className="jupyter-viewer-container">
      <div className="jupyter-viewer-header">
        <Link to="/jupyter" className="back-button">Back to Reports</Link>
        <h1>{notebook.title}</h1>
        <p className="notebook-meta">Last modified: {notebook.lastModified}</p>
      </div>
      
      <div className="jupyter-content">
        <div className="notebook-placeholder">
          <h2>Notebook Viewer</h2>
          <p>This is a placeholder for the Jupyter notebook viewer component.</p>
          <p>In a production environment, this would render the actual notebook content.</p>
          <p>Requested notebook: <strong>{notebookId}</strong></p>
          
          <div className="features-list">
            <h3>Implementation Notes:</h3>
            <ul>
              <li>Viewing Jupyter notebooks typically requires a specialized renderer like nbviewer</li>
              <li>Options for implementation include:
                <ul>
                  <li>Use react-jupyter-notebook package</li>
                  <li>Embed GitHub or NBViewer iframes</li>
                  <li>Convert notebooks to HTML on the server and serve the rendered content</li>
                  <li>Use JupyterLab's web components</li>
                </ul>
              </li>
              <li>For a full implementation, you'd need a backend service to process and render notebooks</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default JupyterViewer;
