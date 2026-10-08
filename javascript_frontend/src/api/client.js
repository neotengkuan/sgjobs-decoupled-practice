/**
 * Thin fetch wrapper around the SGJobs API.
 *
 * This module owns nothing but transport: the base URL, JSON decoding and
 * turning failures into a single ApiError shape. No business logic lives
 * here or anywhere else under src/ - every calculation and every filter
 * decision is made by FastAPI.
 */

/**
 * Base URL for the API.
 *
 * - VITE_API_URL=http://localhost:8000  -> absolute, cross-origin calls.
 * - VITE_API_URL unset or empty         -> same origin, so "/api/..."
 *   goes through the Vite dev proxy. Use this when the backend has no
 *   CORS middleware.
 */
export const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(
  /\/+$/,
  '',
)

export class ApiError extends Error {
  constructor(message, { status = null, detail = '', url = '' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.url = url
  }
}

/** Human-readable target, used in error messages. */
function describeTarget(url) {
  if (!url) {
    return 'this origin (the Vite dev server proxy)'
  }

  try {
    return new URL(url).origin
  } catch {
    return url
  }
}

/**
 * GET a path and return decoded JSON.
 *
 * `cache: 'no-store'` keeps the browser out of the way: the backend
 * already caches the loaded dataset, and the Refresh button must always
 * re-request.
 */
export async function request(path, { signal } = {}) {
  const url = `${API_BASE_URL}${path}`

  let response

  try {
    response = await fetch(url, {
      signal,
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw error
    }

    throw new ApiError(
      `Could not reach the SGJobs API at ${describeTarget(url)}. ` +
        'Is the backend running, and is the URL correct?',
      { url },
    )
  }

  if (!response.ok) {
    let detail = ''

    try {
      const body = await response.json()
      detail = body?.detail || ''
    } catch {
      detail = ''
    }

    throw new ApiError(
      `The API returned ${response.status}${
        detail ? `: ${detail}` : ''
      }`,
      { status: response.status, detail, url },
    )
  }

  return response.json()
}