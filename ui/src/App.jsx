import { NavLink, Route, Routes } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import SessionsPage from './pages/SessionsPage'
import SessionDetailsPage from './pages/SessionDetailsPage'
import ManualReviewPage from './pages/ManualReviewPage'
import ConnectorsPage from './pages/ConnectorsPage'
import PublicationsPage from './pages/PublicationsPage'
import SettingsPage from './pages/SettingsPage'
import { useUI } from './app/ui'

export default function App() {
  const { t } = useUI()

  const navItems = [
    { to: '/', label: t('nav.dashboard') },
    { to: '/sessions', label: t('nav.sessions') },
    { to: '/manual-review', label: t('nav.manualReview') },
    { to: '/connectors', label: t('nav.connectors') },
    { to: '/publications', label: t('nav.publications') },
    { to: '/settings', label: t('nav.settings') },
  ]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <h1>{t('app.title')}</h1>
          <p>{t('app.subtitle')}</p>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/sessions" element={<SessionsPage />} />
          <Route path="/sessions/:sessionId" element={<SessionDetailsPage />} />
          <Route path="/manual-review" element={<ManualReviewPage />} />
          <Route path="/connectors" element={<ConnectorsPage />} />
          <Route path="/publications" element={<PublicationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
