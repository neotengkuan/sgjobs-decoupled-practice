/**
 * Detail Drillthrough endpoints.
 *
 * Row-level lookups against the same main table and bridge tables the
 * Streamlit reference uses. All record lookup lives in FastAPI: this
 * module only chooses a path, forwards the filters, and returns JSON.
 *
 * No filters are sent on the two bridge lookups, because the backend
 * matches those on job_post_id alone - a job shows its complete
 * multi-label history regardless of the active sidebar filters.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/** Job ids are matched as exact strings; a path segment must be encoded. */
function jobPath(jobPostId, suffix = '') {
  return `/api/jobs/${encodeURIComponent(jobPostId)}${suffix}`
}

/**
 * One page of matching job records, in the filtered frame's own order.
 *
 * The reference shows only the first N rows and has no paging controls, so
 * offset is pinned to 0 here too. `limit` is capped at 500 by the backend.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @param {number} limit  25 | 50 | 100 | 250 | 500
 */
export function fetchJobRecords(filters, limit, { signal } = {}) {
  return request(
    withFilterQuery('/api/jobs', filters, [
      ['limit', limit],
      ['offset', 0],
    ]),
    { signal },
  )
}

/**
 * Job-id selector options: the first 10,000 ids of the filtered frame.
 *
 * Duplicates are returned as-is. The main table can hold several rows per
 * job, so the same id legitimately appears more than once, and the
 * reference offers it more than once. Do not deduplicate.
 *
 * @param {Record<string, Array<string|number>>} filters
 */
export function fetchJobIds(filters, { signal } = {}) {
  return request(
    withFilterQuery('/api/jobs/ids', filters, [['limit', 10000]]),
    { signal },
  )
}

/**
 * One job's detail record: the FIRST filtered row carrying this
 * job_post_id, plus the four drillthrough metric values.
 *
 * A job that is not in the current filter context is answered with HTTP 200
 * and meta.found=false, which is a normal empty state rather than an error.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @param {string} jobPostId
 */
export function fetchJobDetail(jobPostId, filters, { signal } = {}) {
  return request(withFilterQuery(jobPath(jobPostId), filters), { signal })
}

/**
 * One job's category-bridge rows. No sidebar filters, matching the backend.
 *
 * @param {string} jobPostId
 */
export function fetchJobCategories(jobPostId, { signal } = {}) {
  return request(jobPath(jobPostId, '/categories'), { signal })
}

/**
 * One job's skill-bridge rows. No sidebar filters, matching the backend.
 *
 * @param {string} jobPostId
 */
export function fetchJobSkills(jobPostId, { signal } = {}) {
  return request(jobPath(jobPostId, '/skills'), { signal })
}