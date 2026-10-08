import { useEffect, useMemo, useState } from 'react'
import { fetchSalaryAnalysis } from '../api/salaryApi.js'

/**
 * Loads the Salary Analysis datasets for the CURRENT sidebar selection.
 *
 * The selections are not owned here - they are passed in from the hook
 * that owns the filters, so both tabs are always describing the same
 * rows. This hook only holds the salary payload and its own
 * loading/error state, which is what keeps a salary failure from
 * affecting the Overview page.
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, refreshToken?: number}} options
 * @returns {{salary: object|null, loading: boolean, error: Error|null}}
 */
export function useSalaryAnalysis(selections, { ready, refreshToken } = {}) {
  const [salary, setSalary] = useState(null)
  const [state, setState] = useState({ loading: true, error: null })

  const selectionKey = useMemo(
    () => JSON.stringify(selections),
    [selections],
  )

  useEffect(() => {
    if (!ready) {
      return undefined
    }

    const controller = new AbortController()

    setState({ loading: true, error: null })

    fetchSalaryAnalysis(selections, { signal: controller.signal })
      .then((payload) => {
        setSalary(payload)
        setState({ loading: false, error: null })
      })
      .catch((error) => {
        if (error?.name === 'AbortError') {
          return
        }

        setState({ loading: false, error })
      })

    return () => controller.abort()
    // selectionKey serialises the selection, so a new object with equal
    // contents does not trigger a refetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, selectionKey, refreshToken])

  return { salary, loading: state.loading, error: state.error }
}