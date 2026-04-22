import { useState } from 'react'
import { api } from '../app/api'
import { useUI } from '../app/ui'

export default function ManualReviewPage() {
  const { t } = useUI()
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setResult(null)
    try {
      const payload = await api.runManualReview({
        title,
        text,
        max_iterations: 3,
        publish_mode: 'internal_only',
      })
      setResult(payload)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>{t('manual.title')}</h2>
          <p>{t('manual.subtitle')}</p>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}
      {result ? <div className="success-box">{t('manual.done').replace('{{status}}', result.status)}</div> : null}

      <form className="card form-card" onSubmit={handleSubmit}>
        <label>
          <span>{t('manual.titleField')}</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t('manual.titlePlaceholder')} />
        </label>
        <label>
          <span>{t('manual.textField')}</span>
          <textarea rows="12" value={text} onChange={(e) => setText(e.target.value)} placeholder={t('manual.textPlaceholder')} />
        </label>
        <button type="submit">{t('manual.submit')}</button>
      </form>
    </section>
  )
}
