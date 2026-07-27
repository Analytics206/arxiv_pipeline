import apiConfig from '../config/api-config';

const requestJson = async (path) => {
  const response = await fetch(`${apiConfig.API_BASE_URL}${path}`);
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    throw new Error(
      payload?.detail || `Research API returned HTTP ${response.status}`
    );
  }
  return payload;
};

export const getResearchCapabilities = () =>
  requestJson('/research/capabilities');

export const getServiceHealth = () => requestJson('/health');

export const listCuratedPapers = ({ offset = 0, limit = 50 } = {}) => {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
  });
  return requestJson(`/research/papers?${params.toString()}`);
};

export const searchResearch = ({
  query,
  limit = 8,
  paperId = '',
  kind = '',
}) => {
  const params = new URLSearchParams({
    query,
    limit: String(limit),
  });
  if (paperId) params.set('paper_id', paperId);
  if (kind) params.append('kind', kind);
  return requestJson(`/research/search?${params.toString()}`);
};

export const getPaperContext = (paperId) => {
  const params = new URLSearchParams({ paper_id: paperId });
  return requestJson(
    `/research/papers/agent-context?${params.toString()}`
  );
};

export const getEvidence = (evidenceId) =>
  requestJson(`/research/evidence/${encodeURIComponent(evidenceId)}`);

export { apiConfig };
