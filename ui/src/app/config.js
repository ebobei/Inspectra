export function getApiBaseUrl() {
  const explicit = import.meta.env.VITE_API_BASE_URL
  if (explicit) return explicit.replace(/\/$/, '')

  return '/api'
}
