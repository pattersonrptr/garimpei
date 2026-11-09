/**
 * Source websites page — full CRUD with create/edit modals and bulk delete.
 */

import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import FormControlLabel from '@mui/material/FormControlLabel'
import IconButton from '@mui/material/IconButton'
import Link from '@mui/material/Link'
import Stack from '@mui/material/Stack'
import Switch from '@mui/material/Switch'
import TextField from '@mui/material/TextField'
import Tooltip from '@mui/material/Tooltip'
import {
  DataGrid,
  type GridColDef,
  type GridPaginationModel,
  type GridRowSelectionModel,
} from '@mui/x-data-grid'
import { useCallback, useState } from 'react'
import { useSnackbar } from 'notistack'
import { useTranslation } from 'react-i18next'
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog'
import { GenericFormModal } from '@/components/common/GenericFormModal'
import { PageHeader } from '@/components/common/PageHeader'
import { usePaginatedResource } from '@/hooks/usePaginatedResource'
import { logger } from '@/lib/logger'
import { EMPTY_SELECTION, selectedRowIds } from '@/lib/selection'
import {
  createSourceWebsite,
  deleteSourceWebsite,
  getSourceWebsites,
  updateSourceWebsite,
} from '@/services/sourceWebsiteService'
import type {
  SourceWebsite,
  SourceWebsiteCreatePayload,
  SourceWebsiteUpdatePayload,
} from '@/types/sourceWebsite'

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface FormState {
  name: string
  baseUrl: string
  isActive: boolean
}

const defaultForm: FormState = { name: '', baseUrl: '', isActive: true }

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SourceWebsitesPage() {
  const { enqueueSnackbar } = useSnackbar()
  const { t } = useTranslation('admin', { keyPrefix: 'sourceWebsites' })
  const { t: tc } = useTranslation()

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })
  const [rowSelection, setRowSelection] = useState<GridRowSelectionModel>(EMPTY_SELECTION)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)

  // Create modal
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<FormState>(defaultForm)
  const [creating, setCreating] = useState(false)

  // Edit modal
  const [editSite, setEditSite] = useState<SourceWebsite | null>(null)
  const [editForm, setEditForm] = useState<FormState>(defaultForm)
  const [saving, setSaving] = useState(false)

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const fetcher = useCallback(
    () =>
      getSourceWebsites({
        limit: paginationModel.pageSize,
        offset: paginationModel.page * paginationModel.pageSize,
      }),
    [paginationModel],
  )

  const { items, total, loading, error, reload } = usePaginatedResource(fetcher)

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function selectedIds(): string[] {
    return selectedRowIds(rowSelection, items)
  }

  function selectionCount(): number {
    return selectedIds().length
  }

  function openEdit(site: SourceWebsite) {
    setEditSite(site)
    setEditForm({ name: site.name, baseUrl: site.baseUrl, isActive: site.isActive })
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  async function handleCreate() {
    if (!createForm.name || !createForm.baseUrl) {
      enqueueSnackbar(t('toast.required'), { variant: 'warning' })
      return
    }
    setCreating(true)
    try {
      const payload: SourceWebsiteCreatePayload = {
        name: createForm.name,
        baseUrl: createForm.baseUrl,
        isActive: createForm.isActive,
      }
      await createSourceWebsite(payload)
      enqueueSnackbar(t('toast.created'), { variant: 'success' })
      setCreateOpen(false)
      setCreateForm(defaultForm)
      reload()
    } catch (err) {
      logger.error('Failed to create source website', { name: createForm.name }, err)
      enqueueSnackbar(t('toast.createFailed'), { variant: 'error' })
    } finally {
      setCreating(false)
    }
  }

  async function handleEdit() {
    if (!editSite) return
    setSaving(true)
    try {
      const payload: SourceWebsiteUpdatePayload = {
        name: editForm.name || undefined,
        baseUrl: editForm.baseUrl || undefined,
        isActive: editForm.isActive,
      }
      await updateSourceWebsite(editSite.id, payload)
      enqueueSnackbar(t('toast.updated'), { variant: 'success' })
      setEditSite(null)
      reload()
    } catch (err) {
      logger.error('Failed to update source website', { id: editSite.id }, err)
      enqueueSnackbar(t('toast.updateFailed'), { variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!deleteId) return
    try {
      await deleteSourceWebsite(deleteId)
      enqueueSnackbar(t('toast.deleted'), { variant: 'success' })
      reload()
    } catch (err) {
      logger.error('Failed to delete source website', { id: deleteId }, err)
      enqueueSnackbar(t('toast.deleteFailed'), { variant: 'error' })
    } finally {
      setDeleteId(null)
    }
  }

  async function handleBulkDelete() {
    setBulkDeleteOpen(false)
    const ids = selectedIds()
    try {
      await Promise.all(ids.map(deleteSourceWebsite))
      enqueueSnackbar(t('toast.bulkDeleted', { count: ids.length }), { variant: 'success' })
      setRowSelection(EMPTY_SELECTION)
      reload()
    } catch (err) {
      logger.error('Failed to bulk delete source websites', { ids }, err)
      enqueueSnackbar(t('toast.bulkDeleteFailed'), { variant: 'error' })
    }
  }

  // ---------------------------------------------------------------------------
  // Shared form fields renderer
  // ---------------------------------------------------------------------------

  function renderFormFields(form: FormState, setForm: React.Dispatch<React.SetStateAction<FormState>>) {
    return (
      <Stack spacing={2} sx={{ pt: 1 }}>
        <TextField
          label={t('fields.name')}
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          required
          fullWidth
          size="small"
        />
        <TextField
          label={t('fields.baseUrl')}
          value={form.baseUrl}
          onChange={(e) => setForm((f) => ({ ...f, baseUrl: e.target.value }))}
          required
          fullWidth
          size="small"
          placeholder="https://example.com"
        />
        <FormControlLabel
          control={
            <Switch
              checked={form.isActive}
              onChange={(e) => setForm((f) => ({ ...f, isActive: e.target.checked }))}
            />
          }
          label={t('fields.active')}
        />
      </Stack>
    )
  }

  // ---------------------------------------------------------------------------
  // Columns
  // ---------------------------------------------------------------------------

  const columns: GridColDef<SourceWebsite>[] = [
    { field: 'name', headerName: t('fields.name'), flex: 1, minWidth: 150 },
    {
      field: 'baseUrl',
      headerName: t('fields.baseUrl'),
      flex: 2,
      minWidth: 200,
      renderCell: ({ value }) => (
        <Link href={value} target="_blank" rel="noopener noreferrer">
          {value}
        </Link>
      ),
    },
    {
      field: 'isActive',
      headerName: t('fields.active'),
      width: 100,
      renderCell: ({ value }) => (
        <Chip
          label={value ? tc('yesNo.yes') : tc('yesNo.no')}
          color={value ? 'success' : 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: tc('columns.actions'),
      width: 100,
      getActions: ({ row }) => [
        <Tooltip title={tc('actions.edit')} key="edit">
          <IconButton size="small" onClick={() => openEdit(row)}>
            <EditIcon fontSize="small" />
          </IconButton>
        </Tooltip>,
        <Tooltip title={tc('actions.delete')} key="delete">
          <IconButton
            size="small"
            color="error"
            onClick={() => setDeleteId(row.id)}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Tooltip>,
      ],
    },
  ]

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Box>
      <PageHeader
        title={t('title')}
        actionLabel={t('new')}
        onAction={() => setCreateOpen(true)}
      />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {t('loadFailed')}
        </Alert>
      )}

      {selectionCount() > 0 && (
        <Box sx={{ mb: 1 }}>
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            size="small"
            onClick={() => setBulkDeleteOpen(true)}
          >
            {tc('actions.deleteSelected')} ({selectionCount()})
          </Button>
        </Box>
      )}

      <DataGrid
        rows={items}
        columns={columns}
        rowCount={total}
        loading={loading}
        paginationMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        pageSizeOptions={[10, 25, 50]}
        checkboxSelection
        rowSelectionModel={rowSelection}
        onRowSelectionModelChange={setRowSelection}
        disableRowSelectionOnClick
        autoHeight
      />

      {/* ── Create modal ─────────────────────────────────────────────── */}
      <GenericFormModal
        open={createOpen}
        title={t('newTitle')}
        onClose={() => {
          setCreateOpen(false)
          setCreateForm(defaultForm)
        }}
        onSave={handleCreate}
        saving={creating}
        saveLabel={tc('actions.create')}
      >
        {renderFormFields(createForm, setCreateForm)}
      </GenericFormModal>

      {/* ── Edit modal ───────────────────────────────────────────────── */}
      <GenericFormModal
        open={editSite !== null}
        title={t('editTitle', { name: editSite?.name ?? '' })}
        onClose={() => setEditSite(null)}
        onSave={handleEdit}
        saving={saving}
      >
        {renderFormFields(editForm, setEditForm)}
      </GenericFormModal>

      {/* ── Single delete confirmation ────────────────────────────────── */}
      <ConfirmationDialog
        open={deleteId !== null}
        title={t('dialogs.deleteTitle')}
        message={t('dialogs.deleteMessage')}
        confirmLabel={tc('actions.delete')}
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />

      {/* ── Bulk delete confirmation ──────────────────────────────────── */}
      <ConfirmationDialog
        open={bulkDeleteOpen}
        title={t('dialogs.bulkDeleteTitle')}
        message={t('dialogs.bulkDeleteMessage', { count: selectionCount() })}
        confirmLabel={tc('actions.delete')}
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkDeleteOpen(false)}
      />
    </Box>
  )
}


