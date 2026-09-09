import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useLang } from '../i18n'

const EXAMPLES = ['example.com', '8.8.8.8', 'john@example.com', '@githubuser']

export default function NewInvestigation() {
  const { t } = useLang()
  const navigate = useNavigate()
  const [raw, setRaw] = useState('')
  const [image, setImage] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const inv = await api.createInvestigation(raw.trim())
      navigate(`/inv/${inv.id}`)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const upload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setBusy(true)
    setError('')
    try {
      const inv = await api.uploadImage(file)
      navigate(`/inv/${inv.id}`)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-head"><h2>{t('new.title')}</h2></div>
      <div className="panel">
        <h3>{t('new.tab-text')}</h3>
        <p className="muted">{t('new.tab-text-desc')}</p>
        <form onSubmit={submit}>
          <textarea rows={3} value={raw}
            onChange={(e) => setRaw(e.target.value)}
            placeholder={t('new.placeholder')} />
          <div className="row-buttons">
            <button className="btn btn-primary" disabled={busy || !raw.trim()}>
              {busy ? t('new.running') : t('new.run')}
            </button>
          </div>
        </form>
        <div className="examples">
          {EXAMPLES.map((x) => (
            <button key={x} className="chip" onClick={() => setRaw(x)}>{x}</button>
          ))}
        </div>
      </div>

      <div className="panel">
        <h3>{t('new.tab-image')}</h3>
        <p className="muted">{t('new.tab-image-desc')}</p>
        <input type="file" accept="image/png,image/jpeg,image/webp" onChange={upload}
          disabled={busy} />
      </div>

      {error && <p className="error">{error}</p>}
    </div>
  )
}