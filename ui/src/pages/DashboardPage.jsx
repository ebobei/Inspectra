import { useEffect, useState } from 'react'
import { api } from '../app/api'
import { useUI } from '../app/ui'

export default function DashboardPage() {
  const { t } = useUI()
  const [metrics, setMetrics] = useState(null)
  const [queue, setQueue] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.getMetrics(), api.getQueue()])
      .then(([metricsPayload, queuePayload]) => {
        setMetrics(metricsPayload)
        setQueue(queuePayload)
      })
      .catch((err) => setError(err.message))
  }, [])

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>{t('dashboard.title')}</h2>
          <p>{t('dashboard.subtitle')}</p>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <div className="card-grid">
        {metrics ? (
          <>
            <div className="card"><strong>{metrics.active_sessions}</strong><span>{t('dashboard.activeSessions')}</span></div>
            <div className="card"><strong>{metrics.paused_sessions}</strong><span>{t('dashboard.pausedSessions')}</span></div>
            <div className="card"><strong>{metrics.error_sessions}</strong><span>{t('dashboard.errorSessions')}</span></div>
            <div className="card"><strong>{metrics.successful_publications}</strong><span>{t('dashboard.successfulPublications')}</span></div>
            <div className="card"><strong>{metrics.failed_publications}</strong><span>{t('dashboard.failedPublications')}</span></div>
          </>
        ) : (
          <div className="card full-width">{t('dashboard.emptyMetrics')}</div>
        )}
      </div>

      <div className="card section-card">
        <h3>{t('dashboard.queueTitle')}</h3>
        {queue ? (
          <div className="queue-grid">
            <div><strong>{queue.queued_jobs}</strong><span>{t('dashboard.queuedJobs')}</span></div>
            <div><strong>{queue.started_jobs}</strong><span>{t('dashboard.startedJobs')}</span></div>
            <div><strong>{queue.failed_jobs}</strong><span>{t('dashboard.failedJobs')}</span></div>
          </div>
        ) : (
          <p>{t('common.loading')}</p>
        )}
      </div>
    </section>
  )
}
