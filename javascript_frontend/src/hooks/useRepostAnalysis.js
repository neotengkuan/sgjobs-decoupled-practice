import { useTabDataset } from './useTabDataset.js'
import { fetchRepostAnalysis } from '../api/repostApi.js'

/**
 * Repost Analysis data for the current sidebar selection.
 *
 * Thin wrapper around useTabDataset. `enabled` should be true only while the
 * Repost Analysis tab is active, so a filter change does not refetch a tab
 * the user is not looking at.
 *
 * Independent state, so a failure here leaves the other tabs untouched.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, enabled?: boolean, refreshToken?: number}} options
 * @returns {{repost: object|null, loading: boolean, error: Error|null, stale: boolean, refetch: () => void}}
 */
export function useRepostAnalysis(selections, options) {
  const { data, loading, error, stale, refetch } = useTabDataset(
    fetchRepostAnalysis,
    selections,
    options,
  )

  return { repost: data, loading, error, stale, refetch }
}