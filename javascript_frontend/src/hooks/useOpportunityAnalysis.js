import { useTabDataset } from './useTabDataset.js'
import { fetchOpportunityAnalysis } from '../api/opportunityApi.js'

/**
 * Opportunity Analysis data for the current sidebar selection.
 *
 * Thin wrapper around useTabDataset. `enabled` should be true only while the
 * Opportunity Analysis tab is active, so a filter change does not refetch a
 * tab the user is not looking at.
 *
 * Independent state, so a failure here leaves the other tabs untouched.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, enabled?: boolean, refreshToken?: number}} options
 * @returns {{opportunity: object|null, loading: boolean, error: Error|null, stale: boolean, refetch: () => void}}
 */
export function useOpportunityAnalysis(selections, options) {
  const { data, loading, error, stale, refetch } = useTabDataset(
    fetchOpportunityAnalysis,
    selections,
    options,
  )

  return { opportunity: data, loading, error, stale, refetch }
}