/**
 * Tooltip field specifications for the Demand & Seniority charts.
 *
 * Each entry pairs a payload field with the reference's tooltip title and
 * format. The scatter builds its tooltip from this list by keeping only
 * the fields the backend actually returned, which is how the reference
 * conditionally adds Views / vacancy, Application rate and Opportunity
 * score.
 */
export const SCATTER_TOOLTIP_FIELDS = [
  { field: 'metadata_job_post_id', title: 'Job ID', kind: 'text' },
  { field: 'category_primary', title: 'Job Function (compat.)', kind: 'text' },
  { field: 'seniority_group', title: 'Seniority', kind: 'text' },
  { field: 'salary_midpoint', title: 'Salary midpoint', kind: 'number' },
  { field: 'number_of_vacancies', title: 'Vacancies', kind: 'number' },
  {
    field: 'applications_per_vacancy',
    title: 'Applications / vacancy',
    kind: 'decimal2',
  },
  { field: 'views_per_vacancy', title: 'Views / vacancy', kind: 'decimal2' },
  { field: 'application_rate', title: 'Application rate', kind: 'percent2' },
  { field: 'opportunity_score', title: 'Opportunity score', kind: 'decimal1' },
]

/**
 * Keep only the tooltip fields the payload actually carries.
 *
 * @param {string[]} fields field names from salary_vs_applications.fields
 * @returns {Array<{field: string, title: string, kind: string}>}
 */
export function activeScatterTooltipFields(fields = []) {
  const present = new Set(fields)

  return SCATTER_TOOLTIP_FIELDS.filter((spec) => present.has(spec.field))
}