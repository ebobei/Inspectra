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
      return normalizeUserFacingError(normalizeErrorPayload(payload, fallback), response.status)
    } catch {
      return fallback
    }
  }

  try {
    const text = await response.text()
    return normalizeUserFacingError(text, response.status) || fallback
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

function normalizeUserFacingError(value, status) {
  const text = String(value || '').trim()
  if (!text) return ''

  if (isHtmlError(text)) {
    if (status === 504 || /gateway time-out|gateway timeout/i.test(text)) {
      return 'Сервис не успел ответить и вернул HTTP 504 Gateway Timeout. Повторите запрос позже или проверьте логи backend/worker.'
    }

    return `Backend вернул техническую HTML-страницу ошибки (HTTP ${status}). Подробности смотрите в логах backend/worker.`
  }

  if (isTechnicalDump(text)) {
    return `Backend вернул техническую ошибку (HTTP ${status}). Подробности смотрите в логах backend/worker.`
  }

  if (text.length > 1200) {
    return `${text.slice(0, 1200)}...`
  }

  return text
}

function isHtmlError(text) {
  return /<!doctype html/i.test(text)
    || /<html[\s>]/i.test(text)
    || /<body[\s>]/i.test(text)
    || /<head[\s>]/i.test(text)
    || /<title>.*<\/title>/i.test(text)
}

function isTechnicalDump(text) {
  return /traceback \(most recent call last\)/i.test(text)
    || /stack trace/i.test(text)
    || /nginx\/\d+/i.test(text)
    || /gateway time-out/i.test(text)
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
