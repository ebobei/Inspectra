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
  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(adminToken ? { 'X-Inspectra-Admin-Token': adminToken } : {}),
        ...(options.headers || {}),
      },
      ...options,
    })
  } catch (err) {
    throw new Error(
      'Backend недоступен. Проверьте, что docker compose запущен, UI открыт через правильный порт, а nginx может проксировать /api в backend.',
    )
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }

  if (response.status === 204) return null
  return response.json()
}

async function readErrorMessage(response) {
  const fallback = `Backend вернул HTTP ${response.status}`
  const contentType = response.headers.get('content-type') || ''

  if (contentType.includes('application/json')) {
    try {
      const payload = await response.json()
      return normalizeErrorPayload(payload, fallback)
    } catch {
      return fallback
    }
  }

  try {
    const text = await response.text()
    return text.trim() || fallback
  } catch {
    return fallback
  }
}

function normalizeErrorPayload(payload, fallback) {
  if (!payload) return fallback

  const detail = payload.detail || payload.message || payload.error
  if (!detail) return fallback

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (!item || typeof item !== 'object') return ''

        const location = Array.isArray(item.loc) ? item.loc.join('.') : ''
        const message = item.msg || item.message || ''
        return [location, message].filter(Boolean).join(': ')
      })
      .filter(Boolean)

    return messages.length ? messages.join('\n') : fallback
  }

  if (typeof detail === 'object') {
    try {
      return JSON.stringify(detail)
    } catch {
      return fallback
    }
  }

  return String(detail)
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
