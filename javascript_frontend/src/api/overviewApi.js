/**
 * The three endpoints this step is allowed to use.
 *
 * Everything else (salary, opportunity, demand, bridge charts, data
 * quality, repost, drillthrough) belongs to later steps.
 *
 * Note there is no aggregation, no scoring and no filtering here: each
 * call forwards the user's selections and returns whatever FastAPI
 * decided.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/**
 * Sidebar descriptors: label, order, help text and option list for each
 * filter. The backend owns this vocabulary.
 *
 * @returns {Promise<{filters: Array<object>, meta: object}>}
 */
export function fetchFilterDescriptors({ signal } = {}) {
  return request('/api/filters', { signal })
}

/**
 * Overview KPIs for a filter selection.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {Promise<{meta: object, primary_kpis: object, bridge_kpis: object, dax_measures: object}>}
 */
export function fetchOverview(filters, { signal } = {}) {
  return request(withFilterQuery('/api/overview', filters), { signal })
}

/**
 * Pre-aggregated Overview chart datasets for a filter selection.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {Promise<{meta: object, charts: object}>}
 */
export function fetchOverviewCharts(filters, { signal } = {}) {
  return request(withFilterQuery('/api/overview/charts', filters), {
    signal,
  })
}