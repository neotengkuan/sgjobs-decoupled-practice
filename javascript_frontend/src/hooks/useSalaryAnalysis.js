import { useTabDataset } from './useTabDataset.js'
import { fetchSalaryAnalysis } from '../api/salaryApi.js'

/**
 * Salary Analysis data for the current sidebar selection.
 *
 * Thin wrapper around useTabDataset; the call signature is unchanged from
 * the version that worked before this hook was extracted.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, refreshToken?: number}} options
 * @returns {{salary: object|null, loading: boolean, error: Error|null}}
 */
export function useSalaryAnalysis(selections, options) {
  const { data, loading, error } = useTabDataset(
    fetchSalaryAnalysis,
    selections,
    options,
  )

  return { salary: data, loading, error }
}