import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import { useLang } from '../i18n'

export default function Social() {
  const { id } = useParams()
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    api.investigationSocial(id).then(setData).catch((e) => setError(e.message))
  }, [id])

  const results = useMemo(() => {
    if (!data || !data.analysis || !data.analysis.comments) return []
    let list = data.analysis.comments
    if (filter === 'positive') list = list.filter((c) => c.sentiment === 'positive')
    if (filter === 'negative') list = list.filter((c) => c.sentiment === 'negative')
    return list
  }, [data, filter])

  if (error) return <p className="error">{error}</p>
  if (!data) return <p>{t('results.loading')}</p>

  const counts = data.analysis.counts || {}

  return (
    <div>
      <div className="page-head">
        <h2>{t('social.title')} {data.handle || ''}</h2>
        <Link to={`/inv/${id}`} className="btn btn-outline">{t('social.back')}</Link>
      </div>

      <section>
        <h3>{t('results.entities')} ({data.platforms.length})</h3>
        {data.platforms.length === 0 && <p className="muted">{t('social.g-social')}</p>}
        <div className="cards">
          {data.platforms.map((p) => (
            <div key={p.platform} className="card">
              <div className="card-title">
                <span className="srcchip">{p.platform}</span>
                <span className="social-handle">@{p.handle}</span>
              </div>
              <div className="card-meta">
                {p.exists === true && <span className="ok">● {t('social.exists')}</span>}
                {p.exists === false && <span className="social-missing">{t('social.missing')}</span>}
                {p.simulated && <span className="social-simulated">◆ {t('social.simulated')}</span>}
                {p.simulated === false && <span className="ok">● {t('social.live')}</span>}
                {p.web_mentions && <span className="ok">● {t('social.web')}</span>}
              </div>
              <div className="card-meta">
                {p.publisher && <span>{t('social.publisher')}: <b>{p.publisher}</b></span>}
                {p.location && <span>{t('social.location')}: {p.location}</span>}
                {p.followers != null && <span>{t('social.followers')}: {p.followers}</span>}
                {p.following != null && <span>{t('social.following')}: {p.following}</span>}
                {p.public_repos != null && <span>{t('social.repos')}: {p.public_repos}</span>}
              </div>
              {p.repos?.length > 0 && (
                <div className="social-repos">
                  {p.repos.slice(0, 5).map((r, i) => (
                    <a key={i} className="social-repo" href={r.url || '#'} target="_blank" rel="noreferrer">
                      {r.name} <span className="muted small">★ {r.stars} | {r.language || ''}</span>
                    </a>
                  ))}
                </div>
              )}
              {(p.posts || p.payloads) && (
                <>
                  <div className="card-meta">
                    <span>{t('social.posts')}: {p.posts_count ?? (p.posts || p.payloads).length}</span>
                    {p.joined && <span>{t('social.time')}: {p.joined.slice(0, 16).replace('T', ' ')}</span>}
                  </div>
                  <div className="social-posts">
                    {(p.posts || p.payloads).slice(0, 4).map((post, i) => (
                      <div key={i} className="social-post">
                        {post.url ? (
                          <a className="social-post-link" href={post.url} target="_blank" rel="noreferrer">
                            {post.text}
                          </a>
                        ) : (
                          <div className="social-post">
                            <div className="social-post-meta">
                              {post.publisher && <b>{post.publisher}</b>}
                              {post.published_at && (
                                <span>{t('social.time')}: {post.published_at.slice(0, 16).replace('T', ' ')}</span>
                              )}
                              {post.location && <span>{t('social.location')}: {post.location}</span>}
                            </div>
                            {post.like_count != null && (
                              <div className="social-post-meta">
                                <span>♥ {post.like_count}</span>
                                <span>💬 {post.comment_count}</span>
                                <span>↗ {post.shares}</span>
                              </div>
                            )}
                            <p className="social-post-text">{typeof post === 'string' ? post : post.text}</p>
                            {post.comments && (
                              <ul className="social-comments">
                                {post.comments.slice(0, 5).map((c, j) => (
                                  <li key={j}>
                                    <span className={`senti senti-${c.sentiment}`}>
                                      {c.sentiment === 'positive' ? '▼' : c.sentiment === 'negative' ? '▲' : '◆'}
                                    </span>
                                    {c.text}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
              <div className="card-actions">
                <a href={p.url || p.posts_url} target="_blank" rel="noreferrer" className="btn btn-sm btn-outline">
                  {p.platform}
                </a>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3>{t('social.analysis')}</h3>
        <div className="chips social-filter">
          <button className={`chip ${filter === 'all' ? 'chip-active' : ''}`} onClick={() => setFilter('all')}>
            {t('social.total')}: {data.analysis.total}
          </button>
          <button className={`chip ${filter === 'positive' ? 'chip-active' : ''}`} onClick={() => setFilter('positive')}>
            {t('social.good')} ({counts.positive})
          </button>
          <button className={`chip ${filter === 'negative' ? 'chip-active' : ''}`} onClick={() => setFilter('negative')}>
            {t('social.bad')} ({counts.negative})
          </button>
          <button className={`chip ${filter === 'neutral' ? 'chip-active' : ''}`} onClick={() => setFilter('neutral')}>
            {t('social.neutral')} ({counts.neutral})
          </button>
          {data.analysis.provider === 'ai' && (
            <span className="chip-label">AI</span>
          )}
        </div>
        {results.length === 0 && <p className="muted">{t('results.no-findings')}</p>}
        <div className="social-comments-list">
          {results.map((c, i) => (
            <div key={i} className={`social-comment senti-${c.sentiment}`}>
              <span className="senti-badge">
                {c.sentiment === 'positive' ? '▼' : c.sentiment === 'negative' ? '▲' : '◆'}
              </span>
              <span className="senti-label">{c.sentiment}</span>
              <span className="senti-lang">{c.lang === 'ar' ? t('social.ar') : c.lang === 'en' ? t('social.en') : ''}</span>
              <span className="senti-text">{c.text}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}