import { useUI } from '../app/ui'

export default function StatusBadge({ value }) {
  const { t } = useUI()
  const normalized = (value || t('status.unknown')).toLowerCase()
  return <span className={`status-badge status-${normalized}`}>{value || t('status.unknown')}</span>
}
