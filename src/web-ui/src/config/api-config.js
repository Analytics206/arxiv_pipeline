// API base URL configuration for Docker Compose and local dev
// Use window._env_ if injected, or fallback to default

const API_BASE_URL =
  window?._env_?.API_BASE_URL ||
  process.env.REACT_APP_API_BASE_URL ||
  (window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'http://api:8000');

export default {
  API_BASE_URL,
};
