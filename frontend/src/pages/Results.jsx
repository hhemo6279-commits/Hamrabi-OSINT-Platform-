import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ConfidenceBadge from '../components/ConfidenceBadge'
import { useLang } from '../i18n'

export default function Results() {
  const { id } = useParams()
  const { t } = useLang()
  const [inv, setInv] = useState(null)
  const [error, setError] = useState('')
  const [reportPath, setReportPath] = useState('')
  const [shareUrl, setShareUrl] = useState('')
  const [copied, setCopied] = useState(false)
  const [ai, setAi] = useState(null)
  const [explaining, setExplaining] = useState({})
  const [aiBusy, setAiBusy] = useState(false)
  const [tagDraft, setTagDraft] = useState('')
  const [suggestions, setSuggestions] = useState(null)

  useEffect(() => {
    api.getInvestigation(id).then(setInv).catch((e) => setError(e.message))
    api.suggestions().then(setSuggestions).catch(() => setSuggestions(null))
  }, [id])

  const saveTags = async (tags) => {
    try {
      const updated = await api.setTags(id, tags)
      setInv(updated)
    } catch (e) {
      setError(e.message)
    }
  }

  const addTag = () => {
    const tg = tagDraft.trim().replace(/\s+/g, '_')
    if (!tg) return
    const current = inv.tags || []
    if (!current.includes(tg)) saveTags([...current, tg])
    setTagDraft('')
  }

  const removeTag = (tg) => saveTags((inv.tags || []).filter((x) => x !== tg))

  const makeReport = async () => {
    try {
      const res = await api.generateReport(id)
      setReportPath(res.path)
      setShareUrl(res.share_url ? `${window.location.origin}${res.share_url}` : '')
    } catch (e) {
      setError(e.message)
    }
  }

  const doExport = async (kind) => {
    try {
      const res = await api[kind](id)
      const blob = new Blob(
        [typeof res === 'string' ? res : JSON.stringify(res, null, 2)],
        { type: kind === 'exportCsv' ? 'text/csv;charset=utf-8' : 'application/json' }
      )
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `enki-${id.slice(0, 8)}-${kind === 'exportCsv' ? 'report.csv' : 'report.json'}`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (e) {
      setError(e.message)
    }
  }

  const copyShare = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch (_) {
      setError('Could not copy link')
    }
  }

  const analyze = async () => {
    setAiBusy(true)
    try {
      const res = await api.aiAnalyze(id)
      setAi(res)
      const updated = await api.getInvestigation(id)
      setInv(updated)
    } catch (e) {
      setError(e.message)
    } finally {
      setAiBusy(false)
    }
  }

  const explain = async (relKey) => {
    if (explaining[relKey]) return
    setExplaining((s) => ({ ...s, [relKey]: true }))
    try {
      const res = await api.aiExplain(id, relKey)
      setExplaining((s) => ({ ...s, [relKey]: res.explanation }))
    } catch (e) {
      setError(e.message)
      setExplaining((s) => ({ ...s, [relKey]: false }))
    }
  }

  if (!inv) return <p>{error || t('results.loading')}</p>

  const hasSocial = inv.findings.some((f) => f.source === 'social')

  return (
    <div>
      {error && <p className="error">{error}</p>}
      <div className="page-head">
        <h2>{inv.raw_input}</h2>
        <div className="row-buttons">
          <Link to={`/inv/${id}/sources`} className="btn btn-ghost">{t('results.sources')}</Link>
          {hasSocial && <Link to={`/inv/${id}/social`} className="btn btn-outline">{t('results.social')}</Link>}
          <Link to={`/inv/${id}/graph`} className="btn btn-outline">{t('results.graph')}</Link>
          <button className="btn btn-outline" onClick={analyze} disabled={aiBusy}>
            {aiBusy ? t('results.analyzing') : inv.ai_summary ? t('results.reanalyze') : t('results.analyze')}
          </button>
          <button className="btn btn-primary" onClick={makeReport}>{t('results.report')}</button>
          <button className="btn btn-outline" onClick={() => doExport('exportJson')}>{t('export.json')}</button>
          <button className="btn btn-outline" onClick={() => doExport('exportCsv')}>{t('export.csv')}</button>
        </div>
      </div>

      {inv.tags && (
        <div className="panel">
          <div className="card-title">{t('tags.title')}</div>
          <div className="chip-row">
            {(inv.tags || []).map((tg) => (
              <span key={tg} className="tag-chip">
                #{tg}
                <button className="tag-x" onClick={() => removeTag(tg)}>×</button>
              </span>
            ))}
            <input
              className="tag-input"
              placeholder={t('tags.placeholder')}
              value={tagDraft}
              onChange={(e) => setTagDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') addTag() }}
            />
            <button className="btn btn-sm btn-outline" onClick={addTag}>{t('tags.add')}</button>
          </div>
        </div>
      )}

      {suggestions && (suggestions.suggestions?.length || suggestions.stats) && (
        <div className="panel">
          <div className="card-title">
            {t('suggest.header')} <span className="chip-label">{t('suggest.hint')}</span>
          </div>
          {suggestions.suggestions?.length > 0 && (
            <ul className="list">
              {suggestions.suggestions.map((s, i) => (
                <li key={i}>
                  <code>{s.type}</code> {s.value}
                  <span className="muted"> ×{s.times_seen}</span>
                </li>
              ))}
            </ul>
          )}
          {suggestions.stats && (
            <div className="card-meta">
              <span>{t('suggest.total')}: {suggestions.stats.total_runs}</span>
              {suggestions.stats.sources?.length > 0 && (
                <span>{t('suggest.top')}: {suggestions.stats.sources.slice(0, 4).join(', ')}</span>
              )}
            </div>
          )}
        </div>
      )}

      {reportPath && <p className="ok">{t('results.report-done')} {reportPath}</p>}
      {shareUrl && (
        <div className="share-row">
          <code className="share-link">{shareUrl}</code>
          <button className="btn btn-sm" onClick={copyShare}>
            {copied ? t('results.copied') : t('results.copy-share')}
          </button>
          <button className="btn btn-sm btn-outline" onClick={() => window.print()}>
            {t('export.print')}
          </button>
        </div>
      )}

      {(inv.ai_summary || ai) && (
        <div className="panel ai-panel">
          <div className="card-title">
            {t('results.ai')}
            <span className="chip-label">
              {ai ? `provider: ${ai.provider}${ai.enabled ? '' : ' (offline)'}` : 'offline'}
            </span>
          </div>
          {inv.ai_classification && (
            <p><b>{t('results.classification')}</b> <span className={`typechip type-${inv.ai_classification}`}>
              {inv.ai_classification}</span></p>
          )}
          <p className="ai-summary">{inv.ai_summary || ai?.summary}</p>
        </div>
      )}

      <section>
        <h3>{t('results.entities')}</h3>
        <div className="chips">
          {inv.entities.map((e) => (
            <Link key={e.id} to={`/inv/${id}/entity/${e.id}`}
              className={`chip typechip type-${e.type}`}
              title={`${e.type} · ${e.id}`}>
              {e.value}
            </Link>
          ))}
        </div>
      </section>

      <section>
        <h3>{t('results.findings')}</h3>
        {inv.findings.length === 0 && <p className="muted">{t('results.no-findings')}</p>}
        <div className="cards">
          {inv.findings.map((f) => (
            f.source === 'page' && f.value.title
              ? <PageCard key={f.key} f={f} />
              : (
                <div key={f.key} className="card">
                  <div className="card-title">
                    <span className="srcchip">{f.source}</span> {f.key}
                  </div>
                  <div className="card-meta"><ConfidenceBadge confidence={f.confidence} /></div>
                  <pre className="json">{JSON.stringify(f.value, null, 2)}</pre>
                </div>
              )
          ))}
        </div>
      </section>

      <section>
        <h3>{t('results.relationships')}</h3>
        {inv.relationships.length === 0 && <p className="muted">{t('results.no-rels')}</p>}
        <ul className="rels">
          {inv.relationships.map((r) => (
            <li key={r.key}>
              <code>{r.source_id.slice(0, 8)}</code> — {r.relation} →{' '}
              <code>{r.target_id.slice(0, 8)}</code>
              <span className="row-buttons">
                <ConfidenceBadge confidence={r.confidence} />
                <button className="btn-sm linklike" onClick={() => explain(r.key)}>
                  {explaining[r.key] ? t('results.explaining') : t('results.explain')}
                </button>
              </span>
              {explaining[r.key] && typeof explaining[r.key] === 'string' && (
                <div className="explanation">{explaining[r.key]}</div>
              )}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function PageCard({ f }) {
  const { t } = useLang()
  const v = f.value
  return (
    <div className="card page-card">
      <div className="card-title">
        <span className="srcchip">page</span>
        <a className="page-link" href={v.url} target="_blank" rel="noreferrer">{v.title}</a>
      </div>
      <div className="card-meta">
        <ConfidenceBadge confidence={f.confidence} />
        {v.host && <span className="muted">{v.host}</span>}
      </div>
      <div className="page-grid">
        {v.final_status && <Info label="HTTP" value={v.final_status} />}
        {v.published_time && <Info label={t('page.published') || 'Published'} value={v.published_time} />}
        {v.modified_time && <Info label={t('page.modified') || 'Modified'} value={v.modified_time} />}
        {v.author && <Info label={t('page.author') || 'Author'} value={v.author} />}
        {v.geo && <Info label={t('page.location') || 'Location'} value={v.geo} />}
        {v.registrant_country && <Info label="Country" value={v.registrant_country} />}
      </div>
      {v.description && <p className="page-desc">{v.description}</p>}
      {v.redirects?.length > 0 && (
        <div className="page-redirs">
          {v.redirects.map((r, i) => (
            <div key={i} className="muted small">
              {r.status} → {r.location}
            </div>
          ))}
        </div>
      )}
      {v.social_links?.length > 0 && (
        <div className="chip-row">
          {v.social_links.map((ln, i) => (
            <a key={i} className="tag-chip" href={ln} target="_blank" rel="noreferrer">{ln}</a>
          ))}
        </div>
      )}
      {v.keywords?.length > 0 && (
        <div className="chip-row">
          {v.keywords.map((k, i) => <span key={i} className="tag-chip k">{k}</span>)}
        </div>
      )}
      {v.text_preview && <div className="muted page-preview">{v.text_preview}</div>}
      <pre className="json">{JSON.stringify(v, null, 2)}</pre>
    </div>
  )
}

function Info({ label, value }) {
  return (
    <div className="page-row">
      <span className="page-label">{label}</span>
      <span className="page-value">{value}</span>
    </div>
  )
}