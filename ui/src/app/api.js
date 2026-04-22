import { getApiBaseUrl } from './config'

const API_BASE_URL = getApiBaseUrl()
const ADMIN_TOKEN_KEY = 'inspectra_admin_token'

export function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || ''
}

export function setAdminToken(value) {
  if (value) {
    localStorage.setItem(ADMIN_TOKEN_KEY, value)
  } else {
    localStorage.removeItem(ADMIN_TOKEN_KEY)
  }
}

async function request(path, options = {}) {
  const adminToken = getAdminToken()
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(adminToken ? { 'X-Inspectra-Admin-Token': adminToken } : {}),
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    try {
      const payload = await response.json()
      detail = payload.detail || payload.message || detail
    } catch {
      // ignore json parsing failure
    }
    throw new Error(detail)
  }

  if (response.status === 204) return null
  return response.json()
}

export const api = {
  getMetrics: () => request('/admin/metrics'),
  getQueue: () => request('/admin/queue'),
  getSessions: () => request('/sessions'),
  getSession: (id) => request(`/sessions/${id}`),
  runSession: (id) => request(`/sessions/${id}/run`, { method: 'POST', body: JSON.stringify({ trigger_type: 'manual' }) }),
  createSession: (payload) => request('/sessions', { method: 'POST', body: JSON.stringify(payload) }),
  getConnectors: () => request('/connectors'),
  createConnector: (payload) => request('/connectors', { method: 'POST', body: JSON.stringify(payload) }),
  testConnector: (id) => request(`/connectors/${id}/test`, { method: 'POST' }),
  getPublications: () => request('/publications'),
  runManualReview: (payload) => request('/reviews/manual', { method: 'POST', body: JSON.stringify(payload) }),
}
