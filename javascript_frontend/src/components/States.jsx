/**
 * Loading / error / empty presentation states.
 */
import { API_BASE_URL } from '../api/client.js'

export function LoadingState({ label = 'Loading…' }) {
  return (
    <div className="state state--loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}

/**
 * Neutral note, used where the reference shows st.info - for example when a
 * bridge table is unavailable.
 */
export function InfoNote({ children }) {
  return (
    <div className="state state--info" role="status">
      {children}
    </div>
  )
}

/**
 * API failure banner.
 *
 * The two most common causes for a browser-side failure are a backend
 * that is not running, and a cross-origin call the backend has not
 * allowed, so both are called out explicitly.
 */
export function ErrorBanner({ error, onRetry, retryLabel = 'Retry' }) {
  if (!error) {
    return null
  }

  const target = API_BASE_URL || '(same origin, via the Vite dev proxy)'
  const isCorsSuspect = !API_BASE_URL

  return (
    <div className="state state--error" role="alert">
      <p className="state__title">Could not load the Overview data.</p>
      <p className="state__message">{error.message}</p>

      <ul className="state__hints">
        <li>
          API base URL: <code>{target}</code>
        </li>
        {isCorsSuspect && (
          <li>
            Leave <code>VITE_API_URL</code> empty to use the Vite proxy, or
            enable CORS on the backend if you call it directly.
          </li>
        )}
        <li>
          Start the API with{' '}
          <code>uvicorn backend.main:app --reload --port 8000</code>.
        </li>
      </ul>

      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  )
}