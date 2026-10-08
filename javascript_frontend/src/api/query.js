/**
 * Query-string building for the sidebar filters.
 *
 * Multi-select filters are sent as REPEATED query parameters, exactly the
 * way the Streamlit frontend sends them:
 *
 *   ?skill_bridge=Python&skill_bridge=SQL
 *
 * The backend declares these as List[...] parameters, so repetition - not
 * a comma-joined value - is what it expects.
 */

/**
 * Build URLSearchParams from a {param: values[]} map.
 *
 * @param {Record<string, Array<string|number>>} filters
 * @returns {URLSearchParams}
 */
export function buildFilterParams(filters = {}) {
  const params = new URLSearchParams()

  for (const [param, values] of Object.entries(filters)) {
    if (!values) {
      continue
    }

    for (const value of values) {
      if (value === null || value === undefined || value === '') {
        continue
      }

      params.append(param, String(value))
    }
  }

  return params
}

/**
 * Append the filter query string to a path.
 *
 * Returns the path unchanged when nothing is selected, so an unfiltered
 * request stays "/api/overview".
 *
 * @param {string} path
 * @param {Record<string, Array<string|number>>} filters
 * @returns {string}
 */
export function withFilterQuery(path, filters = {}) {
  const query = buildFilterParams(filters).toString()

  return query ? `${path}?${query}` : path
}

/**
 * Drop selections the backend no longer offers.
 *
 * Option lists come from /api/filters, so after the data or the filter
 * vocabulary changes, a value kept in UI state might no longer exist.
 * Pruning keeps the request valid and stops the browser from sending
 * values that cannot match anything.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {Array<{param: string, options: Array<string|number>}>} descriptors
 * @returns {Record<string, Array<string|number>>}
 */
export function pruneSelections(selections = {}, descriptors = []) {
  const known = new Map(
    descriptors
      .filter((descriptor) => descriptor.available)
      .map((descriptor) => [
        descriptor.param,
        new Set((descriptor.options || []).map(String)),
      ]),
  )

  const next = {}

  for (const [param, values] of Object.entries(selections)) {
    const allowed = known.get(param)

    if (!allowed || !values?.length) {
      continue
    }

    const kept = values.filter((value) => allowed.has(String(value)))

    if (kept.length) {
      next[param] = kept
    }
  }

  return next
}