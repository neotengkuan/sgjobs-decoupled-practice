/**
 * Notice shown when the data on screen no longer matches the current
 * sidebar selection.
 *
 * A tab whose payload predates the last filter change keeps rendering that
 * payload - so the screen never goes blank - and says so here, instead of
 * pretending the numbers are current.
 */
export function StaleBanner({ show }) {
  if (!show) {
    return null
  }

  return (
    <p className="state state--stale">
      Filters changed since this data was loaded. Open this tab again or
      press Refresh to reload it.
    </p>
  )
}