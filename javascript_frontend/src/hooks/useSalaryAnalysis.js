import { useTabDataset } from './useTabDataset.js'
import { fetchSalaryAnalysis } from '../api/salaryApi.js'

/**
 * Salary Analysis data for the current sidebar selection.
 *
 * Thin wrapper around useTabDataset. `enabled` should be true only while the
 * Salary Analysis tab is active, so a filter change does not refetch a tab
 * the user is not looking at.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, enabled?: boolean, refreshToken?: number}} options
 * @returns {{salary: object|null, loading: boolean, error: Error|null, stale: boolean, refetch: () => void}}
 */
export function useSalaryAnalysis(selections, options) {
  const { data, loading, error, stale, refetch } = useTabDataset(
    fetchSalaryAnalysis,
    selections,
    options,
  )

  return { salary: data, loading, error, stale, refetch }
}