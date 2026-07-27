// Resolve the API against the hostname that served the UI. A browser on a
// second computer cannot resolve Docker's internal `api` service name.
const browserDefault =
  typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://localhost:8000';

const API_BASE_URL =
  (typeof window !== 'undefined' && window._env_?.API_BASE_URL) ||
  process.env.REACT_APP_API_BASE_URL ||
  browserDefault;

const apiConfig = {
  API_BASE_URL: API_BASE_URL.replace(/\/$/, ''),
};

export default apiConfig;
