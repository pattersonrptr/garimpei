/**
 * Search configurations page — full CRUD with create/edit modals and bulk delete.
 */

import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import FormControl from '@mui/material/FormControl'
import FormControlLabel from '@mui/material/FormControlLabel'
import IconButton from '@mui/material/IconButton'
import InputLabel from '@mui/material/InputLabel'
import ListItemText from '@mui/material/ListItemText'
import MenuItem from '@mui/material/MenuItem'
import OutlinedInput from '@mui/material/OutlinedInput'
import Select from '@mui/material/Select'
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
import { useCallback, useEffect, useState } from 'react'
import { useSnackbar } from 'notistack'
import { useTranslation } from 'react-i18next'
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog'
import { GenericFormModal } from '@/components/common/GenericFormModal'
import { PageHeader } from '@/components/common/PageHeader'
import { useAuth } from '@/context/AuthContext'
import { usePaginatedResource } from '@/hooks/usePaginatedResource'
import { logger } from '@/lib/logger'
import {
  createSearchConfig,
  deleteSearchConfig,
  getSearchConfigs,
  updateSearchConfig,
} from '@/services/searchConfigService'
import { getAllSourceWebsites } from '@/services/sourceWebsiteService'
import type { SearchConfig, SearchConfigCreatePayload } from '@/types/searchConfig'
import type { SourceWebsite } from '@/types/sourceWebsite'

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface FormState {
  searchTerm: string
  frequencyDays: number
  preferredTime: string
  isActive: boolean
  sourceWebsiteIds: number[]
}

const defaultForm: FormState = {
  searchTerm: '',
  frequencyDays: 1,
  preferredTime: '08:00',
  isActive: true,
  sourceWebsiteIds: [],
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SearchConfigsPage() {
  const { enqueueSnackbar } = useSnackbar()
  const { userId } = useAuth()
  const { t } = useTranslation('admin', { keyPrefix: 'searchConfigs' })
  const { t: tc } = useTranslation()

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })
  const [rowSelection, setRowSelection] = useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set(),
  })
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)

  // Source websites list for multi-select
  const [sourceWebsites, setSourceWebsites] = useState<SourceWebsite[]>([])

  // Create modal
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<FormState>(defaultForm)
  const [creating, setCreating] = useState(false)

  // Edit modal
  const [editConfig, setEditConfig] = useState<SearchConfig | null>(null)
  const [editForm, setEditForm] = useState<FormState>(defaultForm)
  const [saving, setSaving] = useState(false)

  // ---------------------------------------------------------------------------
  // Load source websites once
  // ---------------------------------------------------------------------------

  useEffect(() => {
    getAllSourceWebsites()
      .then(setSourceWebsites)
      .catch((err) => logger.error('Failed to load source websites', {}, err))
  }, [])

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const fetcher = useCallback(
    () =>
      getSearchConfigs({
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
    if (rowSelection.type !== 'include') return []
    return Array.from(rowSelection.ids) as string[]
  }

  function selectionCount(): number {
    return rowSelection.type === 'include' ? rowSelection.ids.size : 0
  }

  function openEdit(config: SearchConfig) {
    setEditConfig(config)
    setEditForm({
      searchTerm: config.searchTerm,
      frequencyDays: config.frequencyDays,
      preferredTime: config.preferredTime,
      isActive: config.isActive,
      sourceWebsiteIds: config.sourceWebsiteIds,
    })
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  async function handleCreate() {
    if (!createForm.searchTerm) {
      enqueueSnackbar(t('toast.required'), { variant: 'warning' })
      return
    }
    setCreating(true)
    try {
      const payload: SearchConfigCreatePayload = {
        ...createForm,
        userId: userId!,
      }
      await createSearchConfig(payload)
      enqueueSnackbar(t('toast.created'), { variant: 'success' })
      setCreateOpen(false)
      setCreateForm(defaultForm)
      reload()
    } catch (err) {
      logger.error('Failed to create search config', { searchTerm: createForm.searchTerm }, err)
      enqueueSnackbar(t('toast.createFailed'), { variant: 'error' })
    } finally {
      setCreating(false)
    }
  }

  async function handleEdit() {
    if (!editConfig) return
    setSaving(true)
    try {
      await updateSearchConfig(editConfig.id, editForm)
      enqueueSnackbar(t('toast.updated'), { variant: 'success' })
      setEditConfig(null)
      reload()
    } catch (err) {
      logger.error('Failed to update search config', { id: editConfig.id }, err)
      enqueueSnackbar(t('toast.updateFailed'), { variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!deleteId) return
    try {
      await deleteSearchConfig(deleteId)
      enqueueSnackbar(t('toast.deleted'), { variant: 'success' })
      reload()
    } catch (err) {
      logger.error('Failed to delete search config', { id: deleteId }, err)
      enqueueSnackbar(t('toast.deleteFailed'), { variant: 'error' })
    } finally {
      setDeleteId(null)
    }
  }

  async function handleBulkDelete() {
    setBulkDeleteOpen(false)
    const ids = selectedIds()
    try {
      await Promise.all(ids.map(deleteSearchConfig))
      enqueueSnackbar(t('toast.bulkDeleted', { count: ids.length }), { variant: 'success' })
      setRowSelection({ type: 'include', ids: new Set() })
      reload()
    } catch (err) {
      logger.error('Failed to bulk delete search configs', { ids }, err)
      enqueueSnackbar(t('toast.bulkDeleteFailed'), { variant: 'error' })
    }
  }

  // ---------------------------------------------------------------------------
  // Columns
  // ---------------------------------------------------------------------------

  const columns: GridColDef<SearchConfig>[] = [
    { field: 'searchTerm', headerName: t('fields.searchTerm'), flex: 2, minWidth: 180 },
    { field: 'frequencyDays', headerName: t('fields.frequencyDays'), width: 160 },
    { field: 'preferredTime', headerName: t('fields.preferredTime'), width: 150 },
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
  // Shared form fields renderer
  // ---------------------------------------------------------------------------

  function renderFormFields(form: FormState, setForm: React.Dispatch<React.SetStateAction<FormState>>) {
    return (
      <Stack spacing={2} sx={{ pt: 1 }}>
        <TextField
          label={t('fields.searchTerm')}
          value={form.searchTerm}
          onChange={(e) => setForm((f) => ({ ...f, searchTerm: e.target.value }))}
          required
          fullWidth
          size="small"
        />
        <TextField
          label={t('fields.frequencyDays')}
          type="number"
          value={form.frequencyDays}
          onChange={(e) =>
            setForm((f) => ({ ...f, frequencyDays: Number(e.target.value) }))
          }
          inputProps={{ min: 1 }}
          fullWidth
          size="small"
        />
        <TextField
          label={t('fields.preferredTime')}
          type="time"
          value={form.preferredTime}
          onChange={(e) => setForm((f) => ({ ...f, preferredTime: e.target.value }))}
          fullWidth
          size="small"
          InputLabelProps={{ shrink: true }}
        />
        <FormControl fullWidth size="small">
          <InputLabel>{t('fields.sources')}</InputLabel>
          <Select
            multiple
            value={form.sourceWebsiteIds}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                sourceWebsiteIds: e.target.value as number[],
              }))
            }
            input={<OutlinedInput label={t('fields.sources')} />}
            renderValue={(selected) =>
              (selected as number[])
                .map((id) => sourceWebsites.find((s) => Number(s.id) === id)?.name ?? id)
                .join(', ')
            }
          >
            {sourceWebsites.map((site) => (
              <MenuItem key={site.id} value={Number(site.id)}>
                <ListItemText primary={site.name} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>
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
        open={editConfig !== null}
        title={t('editTitle', { name: editConfig?.searchTerm ?? '' })}
        onClose={() => setEditConfig(null)}
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


