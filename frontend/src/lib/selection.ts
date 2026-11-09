/**
 * Resolve a DataGrid row selection to concrete row ids.
 *
 * MUI X 8 reports "select all" as `{ type: 'exclude', ids }` ("every row
 * except these"). Code that only read `type: 'include'` saw an empty
 * selection, so "select all" never offered the bulk actions. With server-side
 * pagination the grid only knows the rows on screen, so "every row" resolves
 * to those (the bulk action then names exactly what it will touch).
 */

import type { GridRowId, GridRowSelectionModel } from '@mui/x-data-grid'

export const EMPTY_SELECTION: GridRowSelectionModel = { type: 'include', ids: new Set() }

export function selectedRowIds<Row extends { id: GridRowId }>(
  selection: GridRowSelectionModel,
  rows: Row[],
): string[] {
  if (selection.type === 'include') return Array.from(selection.ids, String)
  return rows.filter((row) => !selection.ids.has(row.id)).map((row) => String(row.id))
}
