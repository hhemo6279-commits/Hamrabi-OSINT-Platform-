import { Link } from 'react-router-dom'
import { useLang } from '../i18n'

export default function Navbar() {
  const { t, toggle } = useLang()
  return (
    <header className="navbar">
      <Link to="/" className="brand">
        <span className="brand-mark">ENKI</span>
        <span className="brand-sub">{t('brand.sub')}</span>
      </Link>
      <nav className="nav-links">
        <Link to="/">{t('nav.dashboard')}</Link>
        <Link to="/new">{t('nav.new')}</Link>
        <Link to="/compare">{t('nav.compare')}</Link>
        <button className="btn btn-ghost btn-sm" onClick={toggle} title="Language / اللغة">
          {t('nav.short')}
        </button>
      </nav>
    </header>
  )
}