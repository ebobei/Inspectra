import { useEffect, useState } from 'react'
import { api } from '../app/api'
import { useUI } from '../app/ui'
import StatusBadge from '../components/StatusBadge'

export default function PublicationsPage() {
  const { t } = useUI()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.getPublications().then(setItems).catch((err) => setError(err.message))
  }, [])

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>{t('publications.title')}</h2>
          <p>{t('publications.subtitle')}</p>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <div className="card table-card">
        <table>
          <thead>
            <tr><th>{t('common.status')}</th><th>{t('publications.target')}</th><th>{t('publications.mode')}</th><th>{t('publications.published')}</th></tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td><StatusBadge value={item.status} /></td>
                <td>{item.target_system}:{item.target_object_id}</td>
                <td>{item.publication_mode}</td>
                <td>{item.published_at ? new Date(item.published_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
            {items.length === 0 ? <tr><td colSpan="4">{t('publications.noItems')}</td></tr> : null}
          </tbody>
        </table>
      </div>
    </section>
  )
}
