import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../app/api'
import { useUI } from '../app/ui'
import StatusBadge from '../components/StatusBadge'

export default function SessionDetailsPage() {
  const { t } = useUI()
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getSession(sessionId)
      .then(setSession)
      .catch((err) => setError(err.message))
  }, [sessionId])

  if (error) return <div className="error-box">{error}</div>
  if (!session) return <div className="card">{t('common.loading')}</div>

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>{t('sessionDetails.title')}</h2>
          <p>{session.title || session.external_id}</p>
        </div>
        <StatusBadge value={session.status} />
      </header>

      <div className="card-grid compact-grid">
        <div className="card"><strong>{session.source_type}</strong><span>{t('sessionDetails.sourceType')}</span></div>
        <div className="card"><strong>{session.external_id}</strong><span>{t('sessionDetails.externalId')}</span></div>
        <div className="card"><strong>{session.open_findings_count}</strong><span>{t('sessionDetails.openFindings')}</span></div>
        <div className="card"><strong>{session.resolved_findings_count}</strong><span>{t('sessionDetails.resolvedFindings')}</span></div>
      </div>

      <div className="split-layout stack-mobile">
        <div className="card table-card">
          <h3>{t('sessionDetails.findings')}</h3>
          <table>
            <thead>
              <tr>
                <th>{t('common.status')}</th>
                <th>{t('sessionDetails.category')}</th>
                <th>{t('manual.titleField')}</th>
                <th>{t('sessionDetails.repeated')}</th>
              </tr>
            </thead>
            <tbody>
              {session.findings.map((finding) => (
                <tr key={finding.id}>
                  <td><StatusBadge value={finding.status} /></td>
                  <td>{finding.category}</td>
                  <td>
                    <strong>{finding.title}</strong>
                    <div className="muted-text">{finding.description}</div>
                  </td>
                  <td>{finding.times_repeated}</td>
                </tr>
              ))}
              {session.findings.length === 0 ? <tr><td colSpan="4">{t('sessionDetails.noFindings')}</td></tr> : null}
            </tbody>
          </table>
        </div>

        <div className="side-stack">
          <div className="card table-card">
            <h3>{t('sessionDetails.runs')}</h3>
            <table>
              <thead>
                <tr><th>{t('common.status')}</th><th>{t('common.type')}</th><th>{t('sessionDetails.created')}</th></tr>
              </thead>
              <tbody>
                {session.runs.map((run) => (
                  <tr key={run.id}>
                    <td><StatusBadge value={run.status} /></td>
                    <td>{run.run_type}/{run.trigger_type}</td>
                    <td>{new Date(run.created_at).toLocaleString()}</td>
                  </tr>
                ))}
                {session.runs.length === 0 ? <tr><td colSpan="3">{t('sessionDetails.noRuns')}</td></tr> : null}
              </tbody>
            </table>
          </div>

          <div className="card table-card">
            <h3>{t('sessionDetails.publications')}</h3>
            <table>
              <thead>
                <tr><th>{t('common.status')}</th><th>{t('sessionDetails.mode')}</th><th>{t('sessionDetails.published')}</th></tr>
              </thead>
              <tbody>
                {session.publications.map((publication) => (
                  <tr key={publication.id}>
                    <td><StatusBadge value={publication.status} /></td>
                    <td>{publication.publication_mode}</td>
                    <td>{publication.published_at ? new Date(publication.published_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
                {session.publications.length === 0 ? <tr><td colSpan="3">{t('sessionDetails.noPublications')}</td></tr> : null}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}
