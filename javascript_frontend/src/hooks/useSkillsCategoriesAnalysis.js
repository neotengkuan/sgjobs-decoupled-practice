import { useTabDataset } from './useTabDataset.js'
import { fetchSkillsCategoriesAnalysis } from '../api/skillsCategoriesApi.js'

/**
 * Skills & Categories data for the current sidebar selection.
 *
 * Thin wrapper around useTabDataset. `enabled` should be true only while the
 * Skills & Categories tab is active, so a filter change does not refetch a
 * tab the user is not looking at.
 *
 * Independent state, so a failure here leaves the other tabs untouched.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, enabled?: boolean, refreshToken?: number}} options
 * @returns {{bridge: object|null, loading: boolean, error: Error|null, stale: boolean, refetch: () => void}}
 */
export function useSkillsCategoriesAnalysis(selections, options) {
  const { data, loading, error, stale, refetch } = useTabDataset(
    fetchSkillsCategoriesAnalysis,
    selections,
    options,
  )

  return { bridge: data, loading, error, stale, refetch }
}