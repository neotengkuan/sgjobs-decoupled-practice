/**
 * Opportunity Analysis endpoint.
 *
 * One module per tab, alongside overviewApi.js and salaryApi.js.
 *
 * The Opportunity Score itself is a pre-computed dataset column. This
 * module does not derive, rescale or weight it: the backend returns the
 * averages, the ranking and the ranking rule, and nothing is recomputed
 * on the way to the screen.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/**
 * Opportunity Analysis datasets for a filter selection.
 *
 * Multi-select filters are forwarded as repeated query parameters through
 * the same query builder the other tabs use.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {Promise<{
 *   meta: object,
 *   opportunity_band_counts: { available: boolean, data: Array<{'Opportunity Band': string, Jobs: number}> },
 *   top_job_functions: {
 *     available: boolean,
 *     min_jobs: number|null,
 *     fallback_applied: boolean,
 *     data: Array<{'Job Function': string, 'Average Opportunity Score': number, Jobs: number}>
 *   }
 * }>}
 */
export function fetchOpportunityAnalysis(filters, { signal } = {}) {
  return request(withFilterQuery('/api/opportunity/analysis', filters), {
    signal,
  })
}