/**
 * Salary Analysis endpoint.
 *
 * Separate from overviewApi.js on purpose: one module per tab, so a
 * later step can add opportunityApi.js / demandApi.js the same way
 * without growing a single file.
 *
 * Everything the tab needs is computed by the backend: the band counts,
 * the per-job-function average and the five summary measures. This module
 * only forwards the filter selections and returns JSON.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/**
 * Salary Analysis datasets for a filter selection.
 *
 * Multi-select filters are forwarded as repeated query parameters, so
 * { salary_band: ['5K–7K'] } becomes
 * /api/salary/analysis?salary_band=5K%E2%80%937K
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {Promise<{
 *   meta: object,
 *   salary_band_counts: { available: boolean, data: Array<{'Salary Band': string, Jobs: number}> },
 *   average_salary_by_job_function: { available: boolean, data: Array<{'Job Function': string, 'Average Salary': number}> },
 *   summary: {
 *     available: boolean,
 *     jobs_with_salary_data: number|null,
 *     average_salary: number|null,
 *     median_salary: number|null,
 *     minimum_salary_midpoint: number|null,
 *     maximum_salary_midpoint: number|null
 *   }
 * }>}
 */
export function fetchSalaryAnalysis(filters, { signal } = {}) {
  return request(withFilterQuery('/api/salary/analysis', filters), {
    signal,
  })
}