import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import ConfidenceBadge from '../components/ConfidenceBadge'
import { useLang } from '../i18n'

export default function EntityView() {
  const { id, eid } = useParams()
  const { t } = useLang()
  const [inv, setInv] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getInvestigation(id).then(setInv).catch((e) => setError(e.message))
  }, [id])

  if (error) return <p className="error">{error}</p>
  if (!inv) return <p>{t('results.loading')}</p>

  const entity = inv.entities.find((e) => e.id === eid)
  if (!entity) return <p className="error">{t('entity.not-found')}</p>

  const ownFindings = inv.findings.filter((f) =>
    f.query.toLowerCase() === entity.value.toLowerCase() ||
    f.key.toLowerCase().includes(entity.value.toLowerCase()))
  const links = inv.relationships.filter((r) =>
    r.source_id === entity.id || r.target_id === entity.id)
  const nameById = Object.fromEntries(inv.entities.map((e) => [e.id, e.value]))

  return (
    <div>
      <div className="page-head">
        <h2>Entity — {entity.value}</h2>
        <div className="row-buttons">
          <Link to={`/inv/${id}`} className="btn btn-outline">{t('entity.back')}</Link>
          <Link to={`/inv/${id}/sources`} className="btn btn-outline">{t('results.sources')}</Link>
          <Link to={`/inv/${id}/graph`} className="btn btn-primary">{t('results.graph')}</Link>
        </div>
      </div>

      <div className="panel">
        <div className="card-title">
          <span className={`typechip type-${entity.type}`}>{entity.type}</span>
          <span className="chip" title={entity.id}>{entity.id}</span>
        </div>
        <p className="muted">{t('entity.created')} {entity.created_at.slice(0, 19).replace('T', ' ')}</p>
      </div>

      <section>
        <h3>{t('entity.evidence')}</h3>
        {ownFindings.length === 0 && <p className="muted">{t('entity.no-direct')}</p>}
        <div className="cards">
          {ownFindings.map((f) => (
            <div key={f.key} className="card">
              <div className="card-title"><span className="srcchip">{f.source}</span> {f.key}</div>
              <div className="card-meta"><ConfidenceBadge confidence={f.confidence} /></div>
              <pre className="json">{JSON.stringify(f.value, null, 2)}</pre>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3>{t('entity.correlations')}</h3>
        {links.length === 0 && <p className="muted">{t('entity.not-linked')}</p>}
        <ul className="rels">
          {links.map((r) => (
            <li key={r.key}>
              {r.source_id === entity.id ? (
                <>— {r.relation} → <code>{entityDisplay(nameById, r.target_id)}</code></>
              ) : (
                <><code>{entityDisplay(nameById, r.source_id)}</code> — {r.relation} → {t('entity.this')}</>
              )}
              <ConfidenceBadge confidence={r.confidence} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function entityDisplay(map, entityId) {
  return map[entityId] || entityId.slice(0, 12) + '…'
}