export function getApiBaseUrl() {
  const explicit = import.meta.env.VITE_API_BASE_URL
  if (explicit) return explicit.replace(/\/$/, '')

  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8081/api'
  }

  return '/api'
}