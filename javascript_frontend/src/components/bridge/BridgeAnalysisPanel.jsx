import { TopCategoriesChart } from './TopCategoriesChart.jsx'
import { TopSkillsChart } from './TopSkillsChart.jsx'
import { ErrorBanner, LoadingState } from '../States.jsx'
import { StaleBanner } from '../StaleBanner.jsx'

/**
 * Skills & Categories tab body.
 *
 * Layout follows the reference: the multi-label note, then the category and
 * skill charts side by side.
 *
 * Availability flags come straight from the payload, and each chart shows the
 * reference's info message when its bridge is unavailable.
 */
export function BridgeAnalysisPanel({
  bridge,
  loading,
  error,
  stale = false,
  onRetry,
}) {
  if (loading && !bridge) {
    return <LoadingState label="Loading Skills & Categories…" />
  }

  if (error && !bridge) {
    return (
      <ErrorBanner
        error={error}
        onRetry={onRetry}
        retryLabel="Retry Skills & Categories"
      />
    )
  }

  if (!bridge) {
    return null
  }

  return (
    <>
      <StaleBanner show={stale} />

      {/* A failure that left previously loaded data in place. */}
      <ErrorBanner error={error} onRetry={onRetry} />

      <p className="content__meta">
        These visuals use the separate bridge tables. For official
        multi-label Job Function analysis, use the category bridge.
        category_primary remains only for compatibility with the existing
        slicer.
      </p>

      <div className="chart-grid">
        <TopCategoriesChart dataset={bridge.top_categories} />
        <TopSkillsChart dataset={bridge.top_skills} />
      </div>
    </>
  )
}