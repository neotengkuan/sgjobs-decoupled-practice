import { useEffect } from 'react'
import { Metric } from '../KpiCards.jsx'
import { InfoNote, ErrorBanner, LoadingState } from '../States.jsx'
import { StaleBanner } from '../StaleBanner.jsx'
import { OutlierMeasuresTable } from './OutlierMeasuresTable.jsx'
import { FlaggedRecordsTable } from './FlaggedRecordsTable.jsx'
import { fmtNumber, fmtPercent } from '../../utils/format.js'

/**
 * Data Quality & Outliers tab body.
 *
 * Layout follows the reference: the Team 6 treatment note, four metric
 * cards, the review-rule table, the interpretation note, then the review
 * population selector with its capped record table.
 *
 * Everything numeric here is either a backend measure or the Overview
 * issue rate. No threshold, mask or percentage is recomputed.
 */
export function DataQualityPanel({
  quality,
  issueRate,
  loading,
  error,
  stale = false,
  onRetry,
  onReviewPopulationChange,
}) {
  const meta = quality?.meta || {}
  const kpis = quality?.kpis || {}
  const measures = quality?.outlier_measures || []

  const populations = meta.review_populations || []
  const activePopulation = meta.review_population

  // Self-heal if the stored selection is no longer one of the backend's
  // options (for example after the filter vocabulary changed): fall back to
  // the first available label. After the reset the condition is false, so
  // this cannot loop.
  useEffect(() => {
    if (!activePopulation || populations.length === 0) {
      return
    }

    if (!populations.includes(activePopulation)) {
      onReviewPopulationChange(populations[0])
    }
  }, [activePopulation, populations, onReviewPopulationChange])

  if (loading && !quality) {
    return <LoadingState label="Loading Data Quality…" />
  }

  if (error && !quality) {
    return (
      <ErrorBanner
        error={error}
        onRetry={onRetry}
        retryLabel="Retry Data Quality"
      />
    )
  }

  if (!quality) {
    return null
  }

  return (
    <>
      <StaleBanner show={stale} />

      {/* A failure that left previously loaded data in place. */}
      <ErrorBanner error={error} onRetry={onRetry} />

      <p className="content__meta">
        Team 6 treatment is Preserve source, flag anomalies, verify with the
        source owner before changing values. Extreme does not automatically
        mean error.
      </p>

      <div className="metric-grid metric-grid--4">
        <Metric
          label="Rows Needing Source Review"
          value={fmtNumber(kpis.rows_needing_source_review)}
        />
        <Metric
          label="Data Quality Issue Rate"
          value={fmtPercent(issueRate)}
        />
        <Metric
          label="999 Vacancy Records"
          value={fmtNumber(kpis.vacancy_999_records)}
        />
        <Metric
          label="RANDOM_JOB Records"
          value={fmtNumber(kpis.random_job_records)}
        />
      </div>

      <h2 className="section-title">Team 6 Outlier Review</h2>

      <OutlierMeasuresTable measures={measures} />

      <InfoNote>
        Interpretation: these are review populations, not automatic
        deletions. Use median salary for broad summaries where extreme
        salaries distort the mean.
      </InfoNote>

      <h2 className="section-title">Inspect Flagged Records</h2>

      <label className="field">
        <span className="field__label">Review population</span>
        <select
          className="field__control"
          value={activePopulation || ''}
          onChange={(event) =>
            onReviewPopulationChange(event.target.value)
          }
        >
          {/* Options and their order come from the backend, so the
              selector matches meta.review_populations exactly. */}
          {populations.map((population) => (
            <option key={population} value={population}>
              {population}
            </option>
          ))}
        </select>
      </label>

      <FlaggedRecordsTable records={quality.flagged_records || {}} />
    </>
  )
}