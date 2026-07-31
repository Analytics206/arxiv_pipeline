import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  getPaperContext,
  listCuratedPapers,
  searchResearch,
} from '../services/ResearchService';
import '../styles/ResearchWorkspace.css';

const KIND_LABELS = {
  evidence: 'Source evidence',
  claim: 'Paper claim',
  implementation_idea: 'Implementation idea',
};

const ClaimList = ({ title, claims }) => {
  if (!claims?.length) return null;
  return (
    <section className="context-section">
      <h3>{title}</h3>
      <ul className="claim-list">
        {claims.map((claim, index) => (
          <li key={`${title}-${index}`}>
            <span>{claim.statement}</span>
            <small>{claim.evidence_ids.join(', ')}</small>
          </li>
        ))}
      </ul>
    </section>
  );
};

function ResearchWorkspace() {
  const [searchParams] = useSearchParams();
  const requestedPaperId = searchParams.get('paper') || '';
  const [query, setQuery] = useState('coding agent harness workflow ideas');
  const [kind, setKind] = useState('');
  const [paperId, setPaperId] = useState('');
  const [catalog, setCatalog] = useState([]);
  const [results, setResults] = useState(null);
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(false);
  const [contextLoading, setContextLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    listCuratedPapers({ limit: 100 })
      .then(async (data) => {
        setCatalog(data.papers || []);
        if (requestedPaperId) {
          setPaperId(requestedPaperId);
          setContextLoading(true);
          try {
            setContext(await getPaperContext(requestedPaperId));
          } catch (contextError) {
            setError(contextError.message);
          } finally {
            setContextLoading(false);
          }
        }
      })
      .catch((catalogError) => setError(catalogError.message));
  }, [requestedPaperId]);

  const selectedPaper = useMemo(
    () => catalog.find((paper) => paper.paper_id === paperId),
    [catalog, paperId]
  );

  const runSearch = async (event) => {
    event?.preventDefault();
    if (query.trim().length < 3) return;
    setLoading(true);
    setError('');
    try {
      const data = await searchResearch({
        query: query.trim(),
        kind,
        paperId,
        limit: 12,
      });
      setResults(data);
    } catch (searchError) {
      setError(searchError.message);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const openContext = async (selectedId) => {
    setContextLoading(true);
    setError('');
    try {
      setContext(await getPaperContext(selectedId));
    } catch (contextError) {
      setError(contextError.message);
    } finally {
      setContextLoading(false);
    }
  };

  const copyResource = async (resourceUri) => {
    try {
      await navigator.clipboard.writeText(resourceUri);
    } catch {
      setError('The browser could not copy the resource identifier.');
    }
  };

  return (
    <main className="research-workspace">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">Research intelligence</span>
          <h1>Find ideas worth applying</h1>
          <p>
            Search verified claims, source quotes, and implementation ideas
            extracted from curated AI papers.
          </p>
        </div>
        <div className="contract-badge">
          <span>Agent contract</span>
          <strong>read-only · cited · versioned</strong>
        </div>
      </header>

      <form className="research-search-form" onSubmit={runSearch}>
        <label className="query-field">
          <span>What are you trying to improve?</span>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows="3"
            placeholder="For example: recover an agent workflow after tool failure"
          />
        </label>
        <div className="search-filters">
          <label>
            <span>Knowledge type</span>
            <select value={kind} onChange={(event) => setKind(event.target.value)}>
              <option value="">Everything</option>
              <option value="implementation_idea">Implementation ideas</option>
              <option value="claim">Paper claims</option>
              <option value="evidence">Source evidence</option>
            </select>
          </label>
          <label>
            <span>Paper</span>
            <select
              value={paperId}
              onChange={(event) => setPaperId(event.target.value)}
            >
              <option value="">All curated papers</option>
              {catalog.map((paper) => (
                <option key={paper.paper_id} value={paper.paper_id}>
                  {paper.title}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={loading || query.trim().length < 3}>
            {loading ? 'Searching…' : 'Search research'}
          </button>
        </div>
        {selectedPaper && (
          <button
            type="button"
            className="text-button"
            onClick={() => openContext(selectedPaper.paper_id)}
          >
            Open the complete context for {selectedPaper.paper_version_id}
          </button>
        )}
      </form>

      {error && <div className="workspace-error">{error}</div>}

      <div className="workspace-grid">
        <section className="results-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Ranked retrieval</span>
              <h2>Results</h2>
            </div>
            {results && (
              <span>
                {results.papers.length} of {results.budget.requested_papers} requested
              </span>
            )}
          </div>

          {!results && !loading && (
            <div className="empty-state">
              <strong>Ask a concrete engineering question.</strong>
              <p>
                Results preserve the paper, page, model, prompt, and embedding
                provenance needed by both humans and agents.
              </p>
            </div>
          )}

          {results?.papers.length === 0 && (
            <div className="empty-state">
              <strong>No research paper matched.</strong>
              <p>Try a broader question or remove the paper/type filter.</p>
            </div>
          )}

          <div className="result-list">
            {results?.papers.map((paper) => (
              <article className="result-card" key={paper.paper_id}>
                <div className="result-meta">
                  <span className={`kind-pill kind-${paper.tier}`}>
                    {paper.tier === 'evidence_backed'
                      ? 'Evidence backed'
                      : 'Metadata lead'}
                  </span>
                  <span>paper rank {paper.rank}</span>
                  <span>{paper.metadata.categories.slice(0, 3).join(', ')}</span>
                </div>
                <h3>{paper.metadata.title}</h3>
                {paper.metadata.abstract && (
                  <p className="result-text">{paper.metadata.abstract}</p>
                )}
                {paper.research_items.map((item) => (
                  <div className="evidence-preview" key={item.point_id}>
                    <span>{KIND_LABELS[item.kind] || item.kind}</span>
                    <p>{item.text}</p>
                    <blockquote>
                      “{item.evidence[0].quote}”
                      <small>Page {item.evidence[0].page}</small>
                    </blockquote>
                  </div>
                ))}
                <div className="result-actions">
                  {paper.tier === 'evidence_backed' && (
                    <button
                      type="button"
                      onClick={() => openContext(paper.paper_id)}
                    >
                      Open paper context
                    </button>
                  )}
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => copyResource(paper.resource_uri)}
                  >
                    Copy resource URI
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <aside className="context-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Agent-ready package</span>
              <h2>Paper context</h2>
            </div>
          </div>

          {contextLoading && <div className="empty-state">Loading context…</div>}
          {!context && !contextLoading && (
            <div className="empty-state">
              <strong>Select a result to inspect the complete analysis.</strong>
              <p>
                This is the same structured contract an external coding agent
                receives.
              </p>
            </div>
          )}
          {context && !contextLoading && (
            <div className="context-content">
              <span className="resource-uri">{context.resource_uri}</span>
              <h2>{context.analysis.title}</h2>
              <p className="context-tldr">{context.analysis.tldr.statement}</p>

              <div className="tag-list">
                {[...context.analysis.concepts, ...context.analysis.tags]
                  .slice(0, 12)
                  .map((tag, index) => <span key={`${tag}-${index}`}>{tag}</span>)}
              </div>

              <ClaimList title="Methods" claims={context.analysis.methods} />
              <ClaimList title="Results" claims={context.analysis.results} />
              <ClaimList
                title="Limitations"
                claims={context.analysis.limitations}
              />

              {context.analysis.implementation_ideas.length > 0 && (
                <section className="context-section">
                  <h3>Implementation ideas</h3>
                  {context.analysis.implementation_ideas.map((idea, index) => (
                    <article className="idea-card" key={`${idea.title}-${index}`}>
                      <strong>{idea.title}</strong>
                      <p>{idea.description}</p>
                      <small>Agent use: {idea.agent_use}</small>
                    </article>
                  ))}
                </section>
              )}

              <section className="context-section provenance">
                <h3>Provenance</h3>
                <dl>
                  <div><dt>Paper</dt><dd>{context.analysis.paper_version_id}</dd></div>
                  <div><dt>Model</dt><dd>{context.analysis.model}</dd></div>
                  <div><dt>Prompt</dt><dd>{context.analysis.prompt_version}</dd></div>
                  <div><dt>Evidence</dt><dd>{context.analysis.evidence.length} quotes</dd></div>
                </dl>
              </section>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}

export default ResearchWorkspace;
