import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  apiConfig,
  getResearchCapabilities,
  getServiceHealth,
  listCuratedPapers,
} from '../services/ResearchService';
import '../styles/Home.css';

function Home() {
  const [catalog, setCatalog] = useState({ total: 0, papers: [] });
  const [capabilities, setCapabilities] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      listCuratedPapers({ limit: 6 }),
      getResearchCapabilities(),
      getServiceHealth(),
    ])
      .then(([paperData, capabilityData, healthData]) => {
        setCatalog(paperData);
        setCapabilities(capabilityData);
        setHealth(healthData);
      })
      .catch((loadError) => setError(loadError.message));
  }, []);

  return (
    <main className="home-container">
      <section className="home-hero">
        <div>
          <span className="eyebrow">Local research intelligence</span>
          <h1>Turn AI papers into engineering leverage.</h1>
          <p>
            Evidence-backed analyses and implementation ideas, curated for
            coding agents and readable by humans.
          </p>
          <div className="hero-actions">
            <Link to="/research" className="primary-action">
              Search curated research
            </Link>
            <a
              href={`${apiConfig.API_BASE_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="secondary-action"
            >
              Inspect the agent API
            </a>
          </div>
        </div>
        <div className="service-card">
          <div className="service-status">
            <span className={health?.status === 'ok' ? 'status-dot online' : 'status-dot'} />
            {health?.status === 'ok' ? 'Research service online' : 'Connecting…'}
          </div>
          <strong>{catalog.total}</strong>
          <span>curated papers</span>
          <code>{apiConfig.API_BASE_URL}</code>
        </div>
      </section>

      {error && <div className="workspace-error">{error}</div>}

      <section className="product-principles">
        <article>
          <span>01</span>
          <h2>Evidence before eloquence</h2>
          <p>Material claims retain verified quotes and source pages.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Structured for agents</h2>
          <p>Stable JSON contracts can enter a harness without scraping UI.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Ideas you can apply</h2>
          <p>Paper claims stay separate from derived implementation ideas.</p>
        </article>
      </section>

      <section className="library-section">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Curated library</span>
            <h2>Recently analyzed</h2>
          </div>
          <Link to="/research">Search all knowledge →</Link>
        </div>
        <div className="paper-grid">
          {catalog.papers.map((paper) => (
            <article key={paper.paper_id} className="paper-card">
              <div className="paper-card-meta">
                <span>{paper.paper_version_id}</span>
                <span>{paper.page_count} pages</span>
              </div>
              <h3>{paper.title}</h3>
              <div className="paper-stats">
                <span>{paper.claim_count} claims</span>
                <span>{paper.evidence_count} citations</span>
                <span>{paper.implementation_idea_count} ideas</span>
              </div>
              <Link to={`/research?paper=${paper.paper_id}`}>
                Explore this paper
              </Link>
            </article>
          ))}
          {!catalog.papers.length && !error && (
            <div className="empty-state">Loading the curated library…</div>
          )}
        </div>
      </section>

      <section className="agent-access-section">
        <div>
          <span className="eyebrow">Harness integration</span>
          <h2>Use the same knowledge from another computer.</h2>
          <p>
            Point your agent tool at this host’s OpenAPI document. Discovery,
            search, paper context, and evidence lookup are read-only.
          </p>
        </div>
        <div className="endpoint-stack">
          <code>{apiConfig.API_BASE_URL}/openapi.json</code>
          {capabilities?.tools.map((tool) => (
            <span key={tool.name}>
              <strong>{tool.name}</strong>
              {tool.path}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}

export default Home;
