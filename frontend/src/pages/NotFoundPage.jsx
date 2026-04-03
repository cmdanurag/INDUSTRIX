import { Link } from 'react-router-dom'
import './pages.css'

export default function NotFoundPage() {
  return (
    <div className="page-shell page-shell--404">
      <div className="not-found-card">
        <p className="not-found-code">404</p>
        <h1 className="not-found-title">Page not found</h1>
        <p className="not-found-text">
          The page you are looking for does not exist or has been moved.
        </p>
        <nav className="not-found-nav">
          <Link to="/" className="page-link-button">
            Go to dashboard
          </Link>
          <Link to="/event" className="page-link-button page-link-button--ghost">
            Event countdown
          </Link>
        </nav>
      </div>
    </div>
  )
}
