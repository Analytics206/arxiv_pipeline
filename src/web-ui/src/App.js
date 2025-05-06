import React from 'react';
import { Routes, Route } from 'react-router-dom';
import './App.css';

// Components
import NavBar from './components/NavBar';
import Home from './components/Home';
import Neo4jExplorer from './components/Neo4jExplorer';
import MongoDBReports from './components/MongoDBReports';
import QdrantSearch from './components/QdrantSearch';
import JupyterReports from './components/JupyterReports';
import JupyterViewer from './components/JupyterViewer';
import ConfigEditor from './components/ConfigEditor';
import PipelineManagement from './components/PipelineManagement';

function App() {
  return (
    <div className="App">
      <NavBar />
      <div className="content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/neo4j" element={<Neo4jExplorer />} />
          <Route path="/mongodb" element={<MongoDBReports />} />
          <Route path="/qdrant" element={<QdrantSearch />} />
          <Route path="/jupyter" element={<JupyterReports />} />
          <Route path="/jupyter/:notebookId" element={<JupyterViewer />} />
          <Route path="/config" element={<ConfigEditor />} />
          <Route path="/pipelines" element={<PipelineManagement />} />
        </Routes>
      </div>
      <footer className="App-footer">
        <p>ArXiv Pipeline - Data Science Deep Research Tool</p>
      </footer>
    </div>
  );
}

export default App;