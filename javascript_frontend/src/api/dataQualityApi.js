/**
 * Data Quality & Outliers endpoint.
 *
 * One module per tab, alongside the other five.
 *
 * Every quality rule lives in the backend: the review thresholds, the
 * review masks, the vacancy-999 and RANDOM_JOB logic and the flagged-row
 * cap. This module forwards the sidebar filters plus the selected review
 * population and returns the payload untouched.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/**
 * Data Quality datasets for a filter selection and review population.
 *
 * `reviewPopulation` is the label from meta.review_populations. Omit it
 * and the backend applies its own default, which is the first entry of
 * that list - the same default the reference selectbox shows.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @param {string} [reviewPopulation]
 * @param {{signal?: AbortSignal}} [opts]
 * @returns {Promise<{
 *   meta: {
 *     review_population: string,
 *     review_populations: string[],
 *     kpi_denominator: string,
 *     flagged_record_cap: number,
 *     issue_rate_source: string
 *   },
 *   kpis: {
 *     rows_needing_source_review: number|null,
 *     vacancy_999_records: number|null,
 *     random_job_records: number|null
 *   },
 *   outlier_measures: Array<{Area: string, 'Review rule': string, 'Matching rows': number}>,
 *   flagged_records: {
 *     columns: string[],
 *     total_matching: number,
 *     rows_shown: number,
 *     cap: number,
 *     data: Array<object>
 *   }
 * }>}
 */
export function fetchDataQualityAnalysis(
  filters,
  reviewPopulation,
  { signal } = {},
) {
  return request(
    withFilterQuery('/api/data-quality/analysis', filters, [
      ['review_population', reviewPopulation],
    ]),
    { signal },
  )
}