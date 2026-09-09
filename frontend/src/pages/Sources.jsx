import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ConfidenceBadge from '../components/ConfidenceBadge'
import { useLang } from '../i18n'

export default function Sources() {
  const { id } = useParams()
  const { t } = useLang()
  const [inv, setInv] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getInvestigation(id).then(setInv).catch((e) => setError(e.message))
  }, [id])

  if (error) return <p className="error">{error}</p>
  if (!inv) return <p>{t('sources.loading')}</p>

  const counts = {}
  inv.findings.forEach((f) => { counts[f.source] = (counts[f.source] || 0) + 1 })

  return (
    <div>
      <div className="page-head">
        <h2>Sources — {inv.raw_input}</h2>
        <Link to={`/inv/${id}`} className="btn btn-outline">{t('sources.back')}</Link>
      </div>

      <div className="panel">
        <h3>{t('sources.usage')}</h3>
        <div className="chips">
          {Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([src, n]) => (
            <span key={src} className="chip"><span className="srcchip">{src}</span> × {n}</span>
          ))}
        </div>
      </div>

      <section>
        <h3>{t('sources.evidence')}</h3>
        {inv.findings.length === 0 && <p className="muted">{t('results.no-findings')}</p>}
        <div className="table-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t('sources.src')}</th>
                <th>{t('sources.time')}</th>
                <th>{t('sources.query')}</th>
                <th>{t('sources.conf')}</th>
                <th>{t('sources.result')}</th>
              </tr>
            </thead>
            <tbody>
              {inv.findings.map((f) => (
                <tr key={f.key}>
                  <td><span className="srcchip">{f.source}</span></td>
                  <td className="muted">{f.timestamp.slice(0, 19).replace('T', ' ')}</td>
                  <td><code>{f.query}</code></td>
                  <td><ConfidenceBadge confidence={f.confidence} /></td>
                  <td className="tbl-result">{JSON.stringify(f.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}