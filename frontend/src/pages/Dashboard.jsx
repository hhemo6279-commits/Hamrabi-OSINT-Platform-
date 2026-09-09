import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import ConfidenceBadge from '../components/ConfidenceBadge'
import { useLang } from '../i18n'

export default function Dashboard() {
  const { t } = useLang()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [tagFilter, setTagFilter] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.listInvestigations().then(setItems).catch((e) => setError(e.message))
  }, [])

  const allTags = useMemo(
    () => [...new Set(items.flatMap((i) => i.tags || []))].sort(),
    [items]
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items.filter((inv) => {
      if (tagFilter && !(inv.tags || []).includes(tagFilter)) return false
      if (!q) return true
      return (
        inv.raw_input.toLowerCase().includes(q) ||
        inv.entities.some((e) => e.value.toLowerCase().includes(q)) ||
        (inv.tags || []).some((tg) => tg.toLowerCase().includes(q))
      )
    })
  }, [items, query, tagFilter])

  async function onFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const inv = await api.investigateFile(file)
      setItems((prev) => [inv, ...prev])
      e.target.value = ''
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-head">
        <h2>{t('dashboard.title')}</h2>
        <Link to="/new" className="btn btn-primary">{t('dashboard.new')}</Link>
      </div>
      {error && <p className="error">{error}</p>}
      {(items.length > 0 || query) && (
        <div className="filters">
          <input
            className="search-input"
            placeholder={t('dashboard.search')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {allTags.length > 0 && (
            <select className="select" value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}>
              <option value="">{t('dashboard.all')} · {t('dashboard.tags')}</option>
              {allTags.map((tg) => <option key={tg} value={tg}>#{tg}</option>)}
            </select>
          )}
          <label className="btn btn-sm btn-outline file-upload">
            {t('dashboard.upload-file')}
            <input type="file" accept=".txt,.csv,.log,.json"
              onChange={onFile} disabled={busy} />
          </label>
        </div>
      )}
      {filtered.length === 0 && (
        <div className="empty">
          {items.length === 0 ? t('dashboard.empty') : t('social.empty')}
        </div>
      )}
      <div className="cards">
        {filtered.map((inv) => {
          const top = inv.findings.reduce((m, f) => Math.max(m, f.confidence), 0)
          return (
            <div key={inv.id} className="card">
              <div className="card-title">{inv.raw_input}</div>
              <div className="card-meta">
                <span className={`typechip type-${inv.input_type}`}>{inv.input_type}</span>
                <span>{inv.created_at.slice(0, 16).replace('T', ' ')}</span>
              </div>
              {inv.tags?.length > 0 && (
                <div className="chip-row">
                  {inv.tags.map((tg) => <span key={tg} className="tag-chip">#{tg}</span>)}
                </div>
              )}
              <div className="card-meta">
                <span>{inv.entities.length} {t('dashboard.entities')}</span>
                <span>{inv.findings.length} {t('dashboard.findings')}</span>
                <ConfidenceBadge confidence={top} />
              </div>
              <div className="card-actions">
                <Link to={`/inv/${inv.id}`} className="btn btn-sm">{t('dashboard.results')}</Link>
                <Link to={`/inv/${inv.id}/graph`} className="btn btn-sm btn-outline">{t('results.graph')}</Link>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}