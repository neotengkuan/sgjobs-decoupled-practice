import { useCallback } from 'react'
import { useTabDataset } from './useTabDataset.js'
import { fetchDataQualityAnalysis } from '../api/dataQualityApi.js'

/**
 * Data Quality & Outliers data for the current sidebar selection and
 * review population.
 *
 * Thin wrapper around useTabDataset. `enabled` should be true only while the
 * Data Quality tab is active.
 *
 * `reviewPopulation` is passed both to the fetcher and as the hook's
 * extraKey, so changing it refetches this tab only. The fetcher is memoised
 * because useTabDataset keys its effect on the fetcher identity.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{
 *   ready?: boolean,
 *   enabled?: boolean,
 *   refreshToken?: number,
 *   reviewPopulation?: string,
 * }} options
 * @returns {{quality: object|null, loading: boolean, error: Error|null, stale: boolean, refetch: () => void}}
 */
export function useDataQualityAnalysis(
  selections,
  { reviewPopulation, ...options } = {},
) {
  const fetcher = useCallback(
    (filters, opts) =>
      fetchDataQualityAnalysis(filters, reviewPopulation, opts),
    [reviewPopulation],
  )

  const { data, loading, error, stale, refetch } = useTabDataset(
    fetcher,
    selections,
    { ...options, extraKey: reviewPopulation || '' },
  )

  return { quality: data, loading, error, stale, refetch }
}