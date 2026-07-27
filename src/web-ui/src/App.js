import React from 'react';
import { Routes, Route } from 'react-router-dom';
import './App.css';
import { ThemeProvider } from './context/ThemeContext';

// Components
import NavBar from './components/NavBar';
import Home from './components/Home';
import MongoDBReports from './components/MongoDBReports';
import ResearchWorkspace from './components/ResearchWorkspace';
import JupyterReports from './components/JupyterReports';
import JupyterViewer from './components/JupyterViewer';
import ConfigEditor from './components/ConfigEditor';
import PipelineManagement from './components/PipelineManagement';

function App() {
  return (
    <ThemeProvider>
      <div className="App">
      <NavBar />
      <div className="content">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/research" element={<ResearchWorkspace />} />
          <Route path="/mongodb" element={<MongoDBReports />} />
          <Route path="/qdrant" element={<ResearchWorkspace />} />
          <Route path="/jupyter" element={<JupyterReports />} />
          <Route path="/jupyter/:notebookId" element={<JupyterViewer />} />
          <Route path="/config" element={<ConfigEditor />} />
          <Route path="/pipelines" element={<PipelineManagement />} />
        </Routes>
      </div>
      <footer className="App-footer">
        <p>ArXiv Research Intelligence · evidence-backed context for agents and humans</p>
      </footer>
    </div>
    </ThemeProvider>
  );
}

export default App;
