import { Metric } from '../KpiCards.jsx'
import { ErrorBanner, LoadingState } from '../States.jsx'
import { StaleBanner } from '../StaleBanner.jsx'
import { JobBridgeTable } from './JobBridgeTable.jsx'
import {
  fmtCurrency,
  fmtDecimal,
  fmtNumber,
} from '../../utils/format.js'

/**
 * The selected job's detail block: four metrics, the record as JSON, and
 * the job's category and skill rows.
 *
 * The metrics come from the backend's `metrics` block and the record from
 * its `record`, which is the FIRST filtered row carrying this job id - that
 * choice is made by the backend, not here.
 *
 * found=false is a normal empty state: the job is no longer part of the
 * current filter selection, and the reference renders nothing in that case
 * either.
 */
export function JobDetailBlock({ detail, categories, skills }) {
  const meta = detail.data?.meta || {}
  const record = detail.data?.record
  const metrics = detail.data?.metrics || {}

  if (!meta.found || !record) {
    return null
  }

  // The reference renders the record with st.json, stringifying every value
  // and showing null for a missing one.
  const json = JSON.stringify(
    Object.fromEntries(
      Object.entries(record).map(([key, value]) => [
        key,
        value === null || value === undefined ? null : String(value),
      ]),
    ),
    null,
    2,
  )

  return (
    <>
      <StaleBanner show={detail.stale} />

      <ErrorBanner error={detail.error} onRetry={detail.refetch} />

      {meta.matching_rows > 1 && (
        <p className="content__meta">
          {meta.matching_rows} filtered rows share this job id; showing the
          first.
        </p>
      )}

      <div className="metric-grid metric-grid--4">
        <Metric
          label="Salary Midpoint"
          value={fmtCurrency(metrics.salary_midpoint)}
        />
        <Metric
          label="Vacancies"
          value={fmtNumber(metrics.number_of_vacancies)}
        />
        <Metric
          label="Applications / Vacancy"
          value={fmtDecimal(metrics.applications_per_vacancy, 2)}
        />
        <Metric
          label="Opportunity Score"
          value={fmtDecimal(metrics.opportunity_score, 1)}
        />
      </div>

      <pre className="json-block">{json}</pre>

      <div className="drill__columns">
        <section>
          <ErrorBanner
            error={categories.error}
            onRetry={categories.refetch}
          />
          <JobBridgeTable label="All Job Functions from bridge" data={categories.data} />
        </section>

        <section>
          <ErrorBanner error={skills.error} onRetry={skills.refetch} />
          <JobBridgeTable label="All Skills from bridge" data={skills.data} />
        </section>
      </div>
    </>
  )
}