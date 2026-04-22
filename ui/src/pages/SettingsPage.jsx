import { useState } from 'react'
import { getAdminToken, setAdminToken } from '../app/api'
import { useUI } from '../app/ui'

export default function SettingsPage() {
  const { t, locale, setLocale, theme, setTheme } = useUI()
  const [token, setToken] = useState(getAdminToken())
  const [saved, setSaved] = useState(false)

  function handleSave(event) {
    event.preventDefault()
    setAdminToken(token.trim())
    setSaved(true)
    window.setTimeout(() => setSaved(false), 2000)
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h2>{t('settings.title')}</h2>
          <p>{t('settings.subtitle')}</p>
        </div>
      </header>

      <div className="card section-card">
        <h3>{t('settings.tokenTitle')}</h3>
        <form onSubmit={handleSave} className="stack-form">
          <label>
            <span>{t('settings.token')}</span>
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder={t('settings.tokenPlaceholder')}
            />
          </label>
          <div className="button-row">
            <button type="submit">{t('common.save')}</button>
          </div>
          {saved ? <p className="status-inline success">{t('settings.tokenSaved')}</p> : null}
        </form>
      </div>

      <div className="card section-card">
        <h3>{t('settings.uiTitle')}</h3>
        <div className="settings-grid">
          <label>
            <span>{t('common.language')}</span>
            <select value={locale} onChange={(event) => setLocale(event.target.value)}>
              <option value="en">EN</option>
              <option value="ru">RU</option>
            </select>
          </label>
          <div className="theme-setting">
            <span>{t('common.theme')}</span>
            <label className="toggle-row">
              <span>{t('common.light')}</span>
              <button
                type="button"
                className={`theme-toggle ${theme === 'dark' ? 'is-dark' : 'is-light'}`}
                role="switch"
                aria-checked={theme === 'dark'}
                aria-label={t('common.theme')}
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              >
                <span className="theme-toggle-thumb" />
              </button>
              <span>{t('common.dark')}</span>
            </label>
          </div>
        </div>
      </div>

      <div className="card section-card">
        <h3>{t('settings.notesTitle')}</h3>
        <ul className="simple-list">
          <li>{t('settings.localeNote')}</li>
          <li>{t('settings.originsNote')} <code>UI_ALLOWED_ORIGINS</code>.</li>
          <li>{t('settings.protectedNote')} <code>X-Inspectra-Admin-Token</code>.</li>
          <li>{t('settings.webhookNote')} <code>X-Inspectra-Webhook-Secret</code> / <code>WEBHOOK_SHARED_SECRET</code>.</li>
        </ul>
      </div>
    </section>
  )
}
