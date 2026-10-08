import { useTabDataset } from './useTabDataset.js'
import { fetchDemandAnalysis } from '../api/demandApi.js'

/**
 * Demand & Seniority data for the current sidebar selection.
 *
 * Thin wrapper around useTabDataset. `enabled` matters most here: this is
 * the heaviest payload in the app, because the scatter can carry the
 * backend's 25,000-row sample. While another tab is active nothing is
 * fetched, and the previously loaded payload is flagged stale instead.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, enabled?: boolean, refreshToken?: number}} options
 * @returns {{demand: object|null, loading: boolean, error: Error|null, stale: boolean, refetch: () => void}}
 */
export function useDemandAnalysis(selections, options) {
  const { data, loading, error, stale, refetch } = useTabDataset(
    fetchDemandAnalysis,
    selections,
    options,
  )

  return { demand: data, loading, error, stale, refetch }
}