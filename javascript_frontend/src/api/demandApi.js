/**
 * Demand & Seniority endpoint.
 *
 * One module per tab, alongside overviewApi.js, salaryApi.js and
 * opportunityApi.js.
 *
 * Nothing here is computed: the seniority counts, the per-seniority salary
 * average and median, and the scatter sample (already capped and seeded by
 * the backend) all arrive as payload fields.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/**
 * Demand & Seniority datasets for a filter selection.
 *
 * Multi-select filters are forwarded as repeated query parameters through
 * the shared query builder.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {Promise<{
 *   meta: object,
 *   seniority_counts: { available: boolean, data: Array<{'Seniority': string, Jobs: number}> },
 *   average_salary_by_seniority: {
 *     available: boolean,
 *     data: Array<{'Seniority': string, 'Average Salary': number, 'Median Salary': number, Jobs: number}>
 *   },
 *   salary_vs_applications: {
 *     available: boolean,
 *     fields: string[],
 *     sampled: boolean,
 *     rows_before_sample: number,
 *     rows_sampled: number,
 *     data: Array<object>
 *   }
 * }>}
 */
export function fetchDemandAnalysis(filters, { signal } = {}) {
  return request(withFilterQuery('/api/demand/analysis', filters), { signal })
}