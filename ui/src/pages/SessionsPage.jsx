import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../app/api'
import { useUI } from '../app/ui'
import StatusBadge from '../components/StatusBadge'

const initialForm = {
  source_type: 'jira_issue',
  connector_id: '',
  external_id: '',
  title: '',
  max_iterations: 3,
  recheck_enabled: true,
}

const sourceToConnectorType = {
  jira_issue: 'jira',
  gitlab_merge_request: 'gitlab',
  confluence_page: 'confluence',
}

const sourcePlaceholders = {
  jira_issue: 'sessions.jiraPlaceholder',
  gitlab_merge_request: 'sessions.gitlabPlaceholder',
  confluence_page: 'sessions.confluencePlaceholder',
}

export default function SessionsPage() {
  const { t } = useUI()
  const [sessions, setSessions] = useState([])
  const [connectors, setConnectors] = useState([])
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadData = async () => {
    try {
      const [sessionsPayload, connectorsPayload] = await Promise.all([api.getSessions(), api.getConnectors()])
      setSessions(sessionsPayload)
      setConnectors(connectorsPayload)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const filteredConnectors = useMemo(
    () => connectors.filter((item) => item.connector_type === sourceToConnectorType[form.source_type]),
    [connectors, form.source_type],
  )

  useEffect(() => {
    setForm((prev) => ({ ...prev, connector_id: '' }))
  }, [form.source_type])

  async function handleCreate(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      const payload = {
        ...form,
        connector_id: form.connector_id || null,
        max_iterations: Number(form.max_iterations),
      }
      await api.createSession(payload)
      setMessage(t('sessions.created'))
      setForm(initialForm)
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleRun(sessionId) {
    setError('')
    setMessage('')
    try {
      const result = await api.runSession(sessionId)
      setMessage(t('sessions.runFinished').replace('{{status}}', result.status))
      await loadData()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>{t('sessions.title')}</h2>
          <p>{t('sessions.subtitle')}</p>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}
      {message ? <div className="success-box">{message}</div> : null}

      <div className="split-layout">
        <form className="card form-card" onSubmit={handleCreate}>
          <h3>{t('sessions.createTitle')}</h3>
          <label>
            <span>{t('sessions.sourceType')}</span>
            <select value={form.source_type} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
              <option value="jira_issue">{t('sourceTypes.jira_issue')}</option>
              <option value="gitlab_merge_request">{t('sourceTypes.gitlab_merge_request')}</option>
              <option value="confluence_page">{t('sourceTypes.confluence_page')}</option>
            </select>
          </label>
          <label>
            <span>{t('sessions.connector')}</span>
            <select value={form.connector_id} onChange={(e) => setForm({ ...form, connector_id: e.target.value })}>
              <option value="">{t('sessions.selectConnector')}</option>
              {filteredConnectors.map((connector) => (
                <option key={connector.id} value={connector.id}>{connector.name}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('sessions.externalId')}</span>
            <input value={form.external_id} onChange={(e) => setForm({ ...form, external_id: e.target.value })} placeholder={t(sourcePlaceholders[form.source_type])} />
          </label>
          <label>
            <span>{t('sessions.titleField')}</span>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder={t('sessions.titlePlaceholder')} />
          </label>
          <label>
            <span>{t('sessions.maxIterations')}</span>
            <input type="number" min="1" max="10" value={form.max_iterations} onChange={(e) => setForm({ ...form, max_iterations: e.target.value })} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={form.recheck_enabled} onChange={(e) => setForm({ ...form, recheck_enabled: e.target.checked })} />
            <span>{t('sessions.enableRechecks')}</span>
          </label>
          <button type="submit">{t('common.create')}</button>
        </form>

        <div className="card table-card">
          <h3>{t('sessions.existingTitle')}</h3>
          <table>
            <thead>
              <tr>
                <th>{t('sessions.session')}</th>
                <th>{t('common.status')}</th>
                <th>{t('sessions.iterations')}</th>
                <th>{t('sessions.updated')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td>
                    <Link to={`/sessions/${session.id}`}>{session.id.slice(0, 8)}</Link>
                  </td>
                  <td><StatusBadge value={session.status} /></td>
                  <td>{session.iteration_count}/{session.max_iterations}</td>
                  <td>{new Date(session.updated_at).toLocaleString()}</td>
                  <td>
                    <button type="button" className="secondary-button" onClick={() => handleRun(session.id)}>
                      {t('common.run')}
                    </button>
                  </td>
                </tr>
              ))}
              {sessions.length === 0 ? (
                <tr><td colSpan="5">{t('sessions.noItems')}</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
