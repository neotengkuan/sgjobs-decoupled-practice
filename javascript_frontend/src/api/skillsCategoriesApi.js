/**
 * Skills & Categories endpoint (the bridge tables).
 *
 * One module per tab, alongside overviewApi.js, salaryApi.js,
 * opportunityApi.js and demandApi.js.
 *
 * No bridge logic happens here or anywhere else in this frontend: the
 * backend already filtered the bridge rows by the filtered job-id set and
 * counted DISTINCT job postings per name. This module forwards the same
 * repeated filter parameters and returns the two rankings untouched.
 */
import { request } from './client.js'
import { withFilterQuery } from './query.js'

/**
 * Skills & Categories datasets for a filter selection.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {Promise<{
 *   meta: { count_metric: string, filtered_job_ids: number, ... },
 *   top_categories: { available: boolean, data: Array<{Category: string, 'Job Postings': number}> },
 *   top_skills: { available: boolean, data: Array<{Skill: string, 'Job Postings': number}> }
 * }>}
 */
export function fetchSkillsCategoriesAnalysis(filters, { signal } = {}) {
  return request(withFilterQuery('/api/skills-categories/analysis', filters), {
    signal,
  })
}