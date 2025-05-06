import React from 'react';
import '../styles/PlaceholderPage.css';

function ConfigEditor() {
  return (
    <div className="placeholder-container">
      <h1>Configuration Editor</h1>
      <p className="placeholder-subtitle">This page is under development</p>
      <div className="placeholder-content">
        <p>Future functionality will include:</p>
        <ul>
          <li>Edit and save settings in config/default.yaml</li>
          <li>Validation of configuration values</li>
          <li>Configuration templates and presets</li>
          <li>Configuration history and versioning</li>
        </ul>
      </div>
    </div>
  );
}

export default ConfigEditor;
