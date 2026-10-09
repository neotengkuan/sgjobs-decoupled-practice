/**
 * Repost Analysis endpoint.
 *
 * One module per tab, alongside the other six.
 *
 * Every repost measure lives in the backend: the is_reposted coercion, the
 * reposted/non-reposted row counts, the posting-status groups and the
 * salary average and median per status. This module forwards the same
 * repeated filter parameters and returns the payload untouched.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/**
 * Repost Analysis datasets for a filter selection.
 *
 * Count semantics, decided by the backend: every count is a JOB ROW, not a
 * distinct job_post_id value, because the main table can hold more than one
 * row per job. In the salary table "Jobs" is the group size and therefore
 * includes rows without salary, while the average and median are taken over
 * the non-null salary_midpoint values.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {Promise<{
 *   meta: { count_unit: string, repost_rate_source: string, ... },
 *   kpis: {
 *     reposted_rows: number,
 *     total_rows: number,
 *     non_reposted_rows: number
 *   },
 *   posting_status_counts: {
 *     available: boolean,
 *     data: Array<{'Posting Status': string, Jobs: number}>
 *   },
 *   salary_by_posting_status: {
 *     available: boolean,
 *     data: Array<{
 *       'Posting Status': string,
 *       Jobs: number,
 *       'Average Salary': number,
 *       'Median Salary': number
 *     }>
 *   }
 * }>}
 */
export function fetchRepostAnalysis(filters, { signal } = {}) {
  return request(withFilterQuery('/api/repost/analysis', filters), { signal })
}