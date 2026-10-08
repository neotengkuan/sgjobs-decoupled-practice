/**
 * Apply a fixed display order to a list of aggregated rows.
 *
 * Recharts draws a category axis in data order, and has no equivalent of
 * Vega-Lite's `sort=[...]` on an axis. So when the reference chart pins
 * its category axis to a specific list (Salary Band, Opportunity Band),
 * that order has to be applied to the rows here.
 *
 * This only reorders rows the backend already produced and counted. No
 * value is computed, and nothing is filtered out:
 *
 *   - an item in `order` takes its position from that list;
 *   - an item missing from `order` sinks to the end, keeping the relative
 *     order it arrived in (which is what Vega-Lite does with a sort list);
 *   - items absent from the data simply do not appear.
 *
 * @param {Array<object>} rows       rows as returned by the API
 * @param {string} labelKey          field holding the category label
 * @param {string[]} order           the reference's axis order
 * @returns {Array<object>} a new, reordered array
 */
export function orderByRank(rows = [], labelKey, order = []) {
  const rank = new Map(order.map((value, index) => [value, index]))

  return [...rows].sort((a, b) => {
    const rankA = rank.get(a?.[labelKey])
    const rankB = rank.get(b?.[labelKey])

    if (rankA === undefined || rankB === undefined) {
      if (rankA === undefined && rankB === undefined) {
        return 0
      }

      return rankA === undefined ? 1 : -1
    }

    return rankA - rankB
  })
}