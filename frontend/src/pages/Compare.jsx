import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useLang } from '../i18n'

export default function Compare() {
  const { t } = useLang()
  const [items, setItems] = useState([])
  const [left, setLeft] = useState('')
  const [right, setRight] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listInvestigations().then(setItems).catch((e) => setError(e.message))
  }, [])

  async function run() {
    setError('')
    setResult(null)
    if (!left || !right || left === right) {
      setError(t('compare.select'))
      return
    }
    try {
      setResult(await api.compare(left, right))
    } catch (e) {
      setError(e.message)
    }
  }

  const opt = (inv) => (
    <option key={inv.id} value={inv.id}>
      {inv.raw_input.slice(0, 60)}
    </option>
  )

  return (
    <div>
      <div className="page-head">
        <h2>{t('compare.title')}</h2>
        <Link to="/" className="btn btn-outline">{t('compare.back')}</Link>
      </div>
      {error && <p className="error">{error}</p>}
      {items.length < 2 && <div className="empty">{t('compare.select')}</div>}
      {items.length >= 2 && (
        <>
          <div className="filters">
            <select className="select" value={left} onChange={(e) => setLeft(e.target.value)}>
              <option value="">{t('compare.pick')}</option>
              {items.map(opt)}
            </select>
            <select className="select" value={right} onChange={(e) => setRight(e.target.value)}>
              <option value="">{t('compare.pick')}</option>
              {items.map(opt)}
            </select>
            <button className="btn btn-primary" onClick={run}>{t('compare.compare')}</button>
          </div>
          {result && (
            <div className="compare-grid">
              <Section title={t('compare.shared-entities')} values={result.shared_entities} />
              <Section title={t('compare.left-only')} values={result.left_only_entities} />
              <Section title={t('compare.right-only')} values={result.right_only_entities} />
              <Section title={t('compare.shared-sources')} values={result.shared_sources} />
              <Section title={t('compare.shared-findings')} values={result.shared_findings} />
              <Section title={t('compare.shared-rels')} values={result.shared_relationships} />
            </div>
          )}
        </>
      )}
    </div>
  )
}

function Section({ title, values }) {
  const { t } = useLang()
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      {values.length === 0
        ? <div className="muted">{t('compare.empty')}</div>
        : <ul className="list">{values.map((v, i) => <li key={i}>{v}</li>)}</ul>}
    </div>
  )
}