import { useCallback, useEffect, useState } from 'react'
import { useTabDataset } from './useTabDataset.js'
import {
  fetchJobCategories,
  fetchJobDetail,
  fetchJobIds,
  fetchJobRecords,
  fetchJobSkills,
} from '../api/jobsApi.js'

/** The reference's "Rows to display" options and its default (index 2). */
export const ROWS_TO_DISPLAY_OPTIONS = [25, 50, 100, 250, 500]
export const ROWS_TO_DISPLAY_DEFAULT = 100

/**
 * The bridge lookups take no filters, so their request state is keyed on a
 * constant selection. Passing this keeps them out of the filter-change path:
 * changing a sidebar filter must not refetch a job's bridge rows.
 */
const NO_FILTERS = {}

/**
 * Detail Drillthrough state and requests.
 *
 * Five endpoints, five independent pieces of request state, so one failure
 * cannot wipe another: a failing records list leaves the selected job's
 * detail intact, and a failing bridge lookup leaves the records table
 * intact.
 *
 * LOCAL UI STATE
 * --------------
 * This hook owns `rowsToDisplay` and `selectedJobId`, because both are
 * request parameters rather than app-wide state.
 *
 *   rowsToDisplay -> part of the RECORDS request key only, so changing it
 *                    refetches /api/jobs and nothing else.
 *   selectedJobId -> part of the DETAIL and BRIDGE request keys, so picking
 *                    a job issues detail + categories + skills.
 *
 * The sidebar filters live in useDashboardData and are only read.
 *
 * REQUESTS WHEN ACTIVE
 * --------------------
 *   first open        /api/jobs/ids + /api/jobs, then detail + 2 bridges
 *   rows changed      /api/jobs
 *   job picked        detail + categories + skills
 *   filters changed   /api/jobs + /api/jobs/ids + detail (bridges unaffected)
 *
 * @param {Record<string, Array<string|number>>} selections
 * @param {{ready?: boolean, enabled?: boolean, refreshToken?: number}} options
 */
export function useDrillthrough(
  selections,
  { ready, enabled = true, refreshToken } = {},
) {
  const [rowsToDisplay, setRowsToDisplay] = useState(
    ROWS_TO_DISPLAY_DEFAULT,
  )
  const [selectedJobId, setSelectedJobId] = useState()

  const selectJobId = useCallback((jobId) => {
    setSelectedJobId(jobId)
  }, [])

  const recordsFetcher = useCallback(
    (filters, opts) => fetchJobRecords(filters, rowsToDisplay, opts),
    [rowsToDisplay],
  )

  const idsFetcher = useCallback((filters, opts) => fetchJobIds(filters, opts), [])

  const detailFetcher = useCallback(
    (filters, opts) => fetchJobDetail(selectedJobId, filters, opts),
    [selectedJobId],
  )

  const categoriesFetcher = useCallback(
    (_filters, opts) => fetchJobCategories(selectedJobId, opts),
    [selectedJobId],
  )

  const skillsFetcher = useCallback(
    (_filters, opts) => fetchJobSkills(selectedJobId, opts),
    [selectedJobId],
  )

  // ---- Requests ------------------------------------------------------------

  const records = useTabDataset(recordsFetcher, selections, {
    ready,
    enabled,
    refreshToken,
    extraKey: String(rowsToDisplay),
  })

  const ids = useTabDataset(idsFetcher, selections, {
    ready,
    enabled,
    refreshToken,
  })

  // The detail lookup is scoped to the current filters, so it refetches when
  // they change - the backend answers found:false if the job has left the
  // selection.
  const detail = useTabDataset(detailFetcher, selections, {
    ready,
    enabled: enabled && Boolean(selectedJobId),
    refreshToken,
    extraKey: selectedJobId || '',
  })

  // Bridge rows ignore the sidebar filters, so they are keyed on the job id
  // alone and never refetch on a filter change.
  const categories = useTabDataset(categoriesFetcher, NO_FILTERS, {
    enabled: enabled && Boolean(selectedJobId),
    extraKey: selectedJobId || '',
  })

  const skills = useTabDataset(skillsFetcher, NO_FILTERS, {
    enabled: enabled && Boolean(selectedJobId),
    extraKey: selectedJobId || '',
  })

  // ---- Revalidate the selected job ----------------------------------------
  // The option list is authoritative. If the current selection is gone - a
  // filter change removed that job, or it was never set - fall back to the
  // first returned option, which is what the reference selectbox shows.
  // An empty list clears the selection so no stale detail is left on screen.
  const jobIds = ids.data?.job_ids

  useEffect(() => {
    if (!jobIds) {
      return
    }

    if (jobIds.length === 0) {
      setSelectedJobId(undefined)
      return
    }

    if (!selectedJobId || !jobIds.includes(selectedJobId)) {
      setSelectedJobId(jobIds[0])
    }
  }, [jobIds, selectedJobId])

  return {
    rowsToDisplay,
    setRowsToDisplay,
    selectedJobId,
    selectJobId,
    records,
    ids,
    detail,
    categories,
    skills,
  }
}