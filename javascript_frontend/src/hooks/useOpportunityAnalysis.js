import { useTabDataset } from './useTabDataset.js'
import { fetchOpportunityAnalysis } from '../api/opportunityApi.js'

/**
 * Opportunity Analysis data for the current sidebar selection.
 *
 * Independent state, so a failure here leaves the Overview and Salary
 * tabs untouched. See useTabDataset for the shared mechanics.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, refreshToken?: number}} options
 * @returns {{opportunity: object|null, loading: boolean, error: Error|null}}
 */
export function useOpportunityAnalysis(selections, options) {
  const { data, loading, error } = useTabDataset(
    fetchOpportunityAnalysis,
    selections,
    options,
  )

  return { opportunity: data, loading, error }
}