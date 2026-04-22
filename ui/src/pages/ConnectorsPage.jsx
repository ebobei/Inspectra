import { useEffect, useState } from 'react'
import { api } from '../app/api'
import { useUI } from '../app/ui'
import StatusBadge from '../components/StatusBadge'

const initialForm = {
  connector_type: 'jira',
  name: '',
  base_url: '',
  auth_type: 'token',
  secret_plain: '',
}

const placeholders = {
  jira: 'connectors.jiraPlaceholder',
  gitlab: 'connectors.gitlabPlaceholder',
  confluence: 'connectors.confluencePlaceholder',
}

export default function ConnectorsPage() {
  const { t } = useUI()
  const [connectors, setConnectors] = useState([])
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function loadConnectors() {
    try {
      setConnectors(await api.getConnectors())
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    loadConnectors()
  }, [])

  async function handleCreate(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    try {
      await api.createConnector(form)
      setForm(initialForm)
      setMessage(t('connectors.created'))
      await loadConnectors()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleTest(connectorId) {
    setError('')
    setMessage('')
    try {
      const result = await api.testConnector(connectorId)
      setMessage(result.details)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>{t('connectors.title')}</h2>
          <p>{t('connectors.subtitle')}</p>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}
      {message ? <div className="success-box">{message}</div> : null}

      <div className="split-layout">
        <form className="card form-card" onSubmit={handleCreate}>
          <h3>{t('connectors.createTitle')}</h3>
          <label>
            <span>{t('common.type')}</span>
            <select value={form.connector_type} onChange={(e) => setForm({ ...form, connector_type: e.target.value })}>
              <option value="jira">Jira</option>
              <option value="gitlab">GitLab</option>
              <option value="confluence">Confluence</option>
            </select>
          </label>
          <label><span>{t('connectors.name')}</span><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label><span>{t('connectors.baseUrl')}</span><input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder={t(placeholders[form.connector_type])} /></label>
          <label><span>{t('connectors.authType')}</span><select value={form.auth_type} onChange={(e) => setForm({ ...form, auth_type: e.target.value })}><option value="token">token</option><option value="basic">basic</option></select></label>
          <label><span>{t('connectors.secret')}</span><input type="password" value={form.secret_plain} onChange={(e) => setForm({ ...form, secret_plain: e.target.value })} /></label>
          <button type="submit">{t('common.create')}</button>
        </form>

        <div className="card table-card">
          <h3>{t('connectors.configuredTitle')}</h3>
          <table>
            <thead>
              <tr><th>{t('connectors.name')}</th><th>{t('common.type')}</th><th>{t('common.status')}</th><th></th></tr>
            </thead>
            <tbody>
              {connectors.map((connector) => (
                <tr key={connector.id}>
                  <td>{connector.name}<div className="muted-text">{connector.base_url}</div></td>
                  <td>{connector.connector_type}</td>
                  <td><StatusBadge value={connector.is_active ? 'active' : 'inactive'} /></td>
                  <td><button type="button" className="secondary-button" onClick={() => handleTest(connector.id)}>{t('common.test')}</button></td>
                </tr>
              ))}
              {connectors.length === 0 ? <tr><td colSpan="4">{t('connectors.noItems')}</td></tr> : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
