/**
 * My Alerts page — PriceAlert CRUD with DataGrid, create/edit modal,
 * pause/resume toggle, and delete.
 */

import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import PauseIcon from '@mui/icons-material/Pause'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import FormControl from '@mui/material/FormControl'
import FormControlLabel from '@mui/material/FormControlLabel'
import IconButton from '@mui/material/IconButton'
import InputAdornment from '@mui/material/InputAdornment'
import InputLabel from '@mui/material/InputLabel'
import ListItemText from '@mui/material/ListItemText'
import MenuItem from '@mui/material/MenuItem'
import OutlinedInput from '@mui/material/OutlinedInput'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import Switch from '@mui/material/Switch'
import TextField from '@mui/material/TextField'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import {
  DataGrid,
  type GridColDef,
  type GridPaginationModel,
  type GridRowSelectionModel,
} from '@mui/x-data-grid'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useSnackbar } from 'notistack'
import { useTranslation } from 'react-i18next'
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog'
import { GenericFormModal } from '@/components/common/GenericFormModal'
import { PageHeader } from '@/components/common/PageHeader'
import { useAuth } from '@/context/AuthContext'
import { usePaginatedResource } from '@/hooks/usePaginatedResource'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { logger } from '@/lib/logger'
import {
  createPriceAlert,
  deletePriceAlert,
  getPriceAlerts,
  updatePriceAlert,
} from '@/services/priceAlertService'
import {
  getExecutionStatus,
  triggerSearchConfig,
} from '@/services/searchConfigService'
import { getAllSourceWebsites } from '@/services/sourceWebsiteService'
import type { PriceAlert, PriceAlertCreatePayload } from '@/types/priceAlert'
import type { SourceWebsite } from '@/types/sourceWebsite'

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface FormState {
  searchTerm: string
  maxPrice: string
  frequencyMinutes: number
  isActive: boolean
  sourceWebsiteIds: number[]
}

const defaultForm: FormState = {
  searchTerm: '',
  maxPrice: '',
  frequencyMinutes: 60,
  isActive: true,
  sourceWebsiteIds: [],
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AlertsPage() {
  const { enqueueSnackbar } = useSnackbar()
  const { userId } = useAuth()
  const { t } = useTranslation(['alerts', 'common'])

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })
  const [rowSelection, setRowSelection] = useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set(),
  })

  // CRUD state
  const [createOpen, setCreateOpen] = useState(false)
  const [editAlert, setEditAlert] = useState<PriceAlert | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [form, setForm] = useState<FormState>(defaultForm)

  // Source websites for multi-select
  const [sourceWebsites, setSourceWebsites] = useState<SourceWebsite[]>([])

  // Run Now: track which search configs are running  (searchConfigId → status)
  const [runningConfigs, setRunningConfigs] = useState<
    Record<string, 'pending' | 'running'>
  >({})
  const pollingTimers = useRef<Record<string, ReturnType<typeof setInterval>>>(
    {},
  )

  // Last-check timestamps per search config (fetched from execution-status)
  const [lastCheckMap, setLastCheckMap] = useState<Record<string, string>>({})

  // Cleanup polling on unmount
  useEffect(() => {
    const timers = pollingTimers.current
    return () => {
      Object.values(timers).forEach(clearInterval)
    }
  }, [])

  useEffect(() => {
    getAllSourceWebsites().then(setSourceWebsites).catch(() => {})
  }, [])

  // Data fetcher
  const { items, total, loading, error, setPagination, reload } =
    usePaginatedResource(getPriceAlerts)

  // Fetch last-check timestamps for every unique searchConfigId in the list
  useEffect(() => {
    if (!items.length) return

    const uniqueIds = [
      ...new Set(
        items
          .map((a) => a.searchConfigId)
          .filter((id): id is number => id != null),
      ),
    ]

    Promise.allSettled(
      uniqueIds.map((id) =>
        getExecutionStatus(String(id)).then((es) => ({ id, es })),
      ),
    ).then((results) => {
      const map: Record<string, string> = {}
      for (const r of results) {
        if (r.status === 'fulfilled' && r.value.es.startedAt) {
          map[String(r.value.id)] = r.value.es.startedAt
        }
      }
      setLastCheckMap(map)
    })
  }, [items])

  // Sync pagination model → hook
  useEffect(() => {
    setPagination({
      page: paginationModel.page,
      pageSize: paginationModel.pageSize,
    })
  }, [paginationModel, setPagination])

  // Open create modal
  const handleOpenCreate = useCallback(() => {
    setForm(defaultForm)
    setCreateOpen(true)
  }, [])

  // Open edit modal
  const handleOpenEdit = useCallback((alert: PriceAlert) => {
    setForm({
      searchTerm: alert.searchTerm,
      maxPrice: String(alert.maxPrice),
      frequencyMinutes: alert.frequencyMinutes,
      isActive: alert.isActive,
      sourceWebsiteIds: alert.sourceWebsiteIds,
    })
    setEditAlert(alert)
  }, [])

  // Create
  const handleCreate = useCallback(async () => {
    if (!userId) return
    try {
      const payload: PriceAlertCreatePayload = {
        searchTerm: form.searchTerm.trim(),
        maxPrice: parseFloat(form.maxPrice),
        userId,
        isActive: form.isActive,
        frequencyMinutes: form.frequencyMinutes,
        sourceWebsiteIds: form.sourceWebsiteIds,
      }
      await createPriceAlert(payload)
      enqueueSnackbar(t('toast.created'), { variant: 'success' })
      setCreateOpen(false)
      reload()
    } catch (err) {
      logger.error('Failed to create alert', {}, err)
      enqueueSnackbar(t('toast.createFailed'), { variant: 'error' })
    }
  }, [form, userId, enqueueSnackbar, reload, t])

  // Update
  const handleUpdate = useCallback(async () => {
    if (!editAlert) return
    try {
      await updatePriceAlert(editAlert.id, {
        searchTerm: form.searchTerm.trim(),
        maxPrice: parseFloat(form.maxPrice),
        isActive: form.isActive,
        frequencyMinutes: form.frequencyMinutes,
        sourceWebsiteIds: form.sourceWebsiteIds,
      })
      enqueueSnackbar(t('toast.updated'), { variant: 'success' })
      setEditAlert(null)
      reload()
    } catch (err) {
      logger.error('Failed to update alert', {}, err)
      enqueueSnackbar(t('toast.updateFailed'), { variant: 'error' })
    }
  }, [editAlert, form, enqueueSnackbar, reload, t])

  // Toggle pause/active
  const handleToggleActive = useCallback(
    async (alert: PriceAlert) => {
      try {
        await updatePriceAlert(alert.id, { isActive: !alert.isActive })
        enqueueSnackbar(
          alert.isActive ? t('toast.paused') : t('toast.resumed'),
          { variant: 'info' },
        )
        reload()
      } catch (err) {
        logger.error('Failed to toggle alert', {}, err)
        enqueueSnackbar(t('toast.updateFailed'), { variant: 'error' })
      }
    },
    [enqueueSnackbar, reload, t],
  )

  // Delete
  const handleDelete = useCallback(async () => {
    if (!deleteId) return
    try {
      await deletePriceAlert(deleteId)
      enqueueSnackbar(t('toast.deleted'), { variant: 'success' })
      setDeleteId(null)
      reload()
    } catch (err) {
      logger.error('Failed to delete alert', {}, err)
      enqueueSnackbar(t('toast.deleteFailed'), { variant: 'error' })
    }
  }, [deleteId, enqueueSnackbar, reload, t])

  // Bulk delete
  const handleBulkDelete = useCallback(async () => {
    const ids =
      rowSelection.type === 'include'
        ? Array.from(rowSelection.ids).map(String)
        : []
    try {
      await Promise.all(ids.map(deletePriceAlert))
      enqueueSnackbar(t('toast.bulkDeleted', { count: ids.length }), { variant: 'success' })
      setBulkDeleteOpen(false)
      setRowSelection({ type: 'include', ids: new Set() })
      reload()
    } catch (err) {
      logger.error('Bulk delete failed', {}, err)
      enqueueSnackbar(t('toast.bulkDeleteFailed'), { variant: 'error' })
    }
  }, [rowSelection, enqueueSnackbar, reload, t])

  // Run Now — trigger scraper search and poll for completion
  const handleRunNow = useCallback(
    async (alert: PriceAlert) => {
      const scId = alert.searchConfigId
      if (!scId) {
        enqueueSnackbar(t('runNow.noConfig'), {
          variant: 'warning',
        })
        return
      }
      const scIdStr = String(scId)

      // Mark as running in UI
      setRunningConfigs((prev) => ({ ...prev, [scIdStr]: 'pending' }))

      try {
        await triggerSearchConfig(scIdStr)
        enqueueSnackbar(t('runNow.triggered'), {
          variant: 'info',
        })
        setRunningConfigs((prev) => ({ ...prev, [scIdStr]: 'running' }))

        // Start polling every 5 seconds
        const timer = setInterval(async () => {
          try {
            const execStatus = await getExecutionStatus(scIdStr)
            if (
              execStatus.status === 'success' ||
              execStatus.status === 'failed'
            ) {
              clearInterval(timer)
              delete pollingTimers.current[scIdStr]
              setRunningConfigs((prev) => {
                const next = { ...prev }
                delete next[scIdStr]
                return next
              })
              // Update last-check timestamp immediately
              if (execStatus.startedAt) {
                setLastCheckMap((prev) => ({
                  ...prev,
                  [scIdStr]: execStatus.startedAt!,
                }))
              }
              reload()
              enqueueSnackbar(
                execStatus.status === 'success'
                  ? t('runNow.done', { count: execStatus.resultsCount ?? 0 })
                  : t('runNow.failed', {
                      error: execStatus.errorMessage ?? t('common:status.unknownError'),
                    }),
                {
                  variant:
                    execStatus.status === 'success' ? 'success' : 'error',
                },
              )
            }
          } catch {
            // ignore polling errors
          }
        }, 5000)

        pollingTimers.current[scIdStr] = timer
      } catch (err) {
        setRunningConfigs((prev) => {
          const next = { ...prev }
          delete next[scIdStr]
          return next
        })
        const response =
          err instanceof Error && 'response' in err
            ? (
                err as unknown as {
                  response?: {
                    status?: number
                    data?: { errors?: { detail?: string }[] }
                  }
                }
              ).response
            : undefined
        const is409 = response?.status === 409
        // 403 = plan limit (e.g. ran recently): show the API's explanation
        const planLimitDetail =
          response?.status === 403 ? response.data?.errors?.[0]?.detail : undefined
        enqueueSnackbar(
          is409
            ? t('runNow.alreadyRunning')
            : (planLimitDetail ?? t('runNow.triggerFailed')),
          { variant: is409 || planLimitDetail ? 'warning' : 'error' },
        )
      }
    },
    [enqueueSnackbar, reload, t],
  )

  // Helper: source name by ID
  const sourceName = useCallback(
    (id: number) => sourceWebsites.find((s) => String(s.id) === String(id))?.name ?? `#${id}`,
    [sourceWebsites],
  )

  // Form fields (shared by create/edit)
  const formFields = (
    <Stack spacing={2} sx={{ mt: 1 }}>
      <TextField
        label={t('fields.searchTerm')}
        fullWidth
        required
        value={form.searchTerm}
        onChange={(e) => setForm((f) => ({ ...f, searchTerm: e.target.value }))}
      />
      <TextField
        label={t('fields.maxPrice')}
        fullWidth
        required
        type="number"
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">R$</InputAdornment>
            ),
          },
        }}
        value={form.maxPrice}
        onChange={(e) => setForm((f) => ({ ...f, maxPrice: e.target.value }))}
      />
      <TextField
        label={t('fields.frequency')}
        fullWidth
        type="number"
        value={form.frequencyMinutes}
        onChange={(e) =>
          setForm((f) => ({
            ...f,
            frequencyMinutes: parseInt(e.target.value, 10) || 60,
          }))
        }
      />
      <FormControl fullWidth>
        <InputLabel>{t('fields.sources')}</InputLabel>
        <Select
          multiple
          value={form.sourceWebsiteIds}
          onChange={(e) => {
            const val = e.target.value
            setForm((f) => ({
              ...f,
              sourceWebsiteIds:
                typeof val === 'string'
                  ? val.split(',').map(Number)
                  : (val as number[]),
            }))
          }}
          input={<OutlinedInput label={t('fields.sources')} />}
          renderValue={(selected) =>
            selected.map((id) => sourceName(id)).join(', ')
          }
        >
          {sourceWebsites
            .filter((sw) => sw.isActive)
            .map((sw) => (
              <MenuItem key={sw.id} value={Number(sw.id)}>
                <ListItemText primary={sw.name} />
              </MenuItem>
            ))}
        </Select>
      </FormControl>
      <FormControlLabel
        control={
          <Switch
            checked={form.isActive}
            onChange={(e) =>
              setForm((f) => ({ ...f, isActive: e.target.checked }))
            }
          />
        }
        label={t('fields.active')}
      />
    </Stack>
  )

  // DataGrid columns
  const columns: GridColDef<PriceAlert>[] = [
    {
      field: 'searchTerm',
      headerName: t('columns.keyword'),
      flex: 1,
      minWidth: 150,
    },
    {
      field: 'maxPrice',
      headerName: t('columns.maxPrice'),
      width: 120,
      renderCell: ({ value }) => formatCurrency(value as number),
    },
    {
      field: 'isActive',
      headerName: t('columns.status'),
      width: 110,
      renderCell: ({ value }) => (
        <Chip
          size="small"
          label={value ? t('common:status.active') : t('common:status.paused')}
          color={value ? 'success' : 'default'}
        />
      ),
    },
    {
      field: 'sourceWebsiteIds',
      headerName: t('columns.sources'),
      width: 180,
      renderCell: ({ value }) => {
        const ids = value as number[]
        if (!ids?.length) return '—'
        return (
          <Stack direction="row" spacing={0.5} flexWrap="wrap">
            {ids.map((id) => (
              <Chip
                key={id}
                size="small"
                label={sourceName(id)}
                variant="outlined"
                sx={{ height: 22, fontSize: '0.75rem' }}
              />
            ))}
          </Stack>
        )
      },
    },
    {
      field: 'frequencyMinutes',
      headerName: t('columns.frequency'),
      width: 110,
      renderCell: ({ value }) => t('common:units.minutes', { count: value }),
    },
    {
      field: 'lastTriggeredAt',
      headerName: t('columns.lastCheck'),
      width: 170,
      renderCell: ({ row }) => {
        const scId = row.searchConfigId ? String(row.searchConfigId) : null
        const ts = scId ? lastCheckMap[scId] : null
        return ts ? formatDateTime(ts) : t('common:status.never')
      },
    },
    {
      field: 'actions',
      headerName: t('columns.actions'),
      width: 190,
      sortable: false,
      filterable: false,
      renderCell: ({ row }) => {
        const scId = row.searchConfigId ? String(row.searchConfigId) : null
        const isRunning = scId ? scId in runningConfigs : false
        return (
          <Stack direction="row" spacing={0.5}>
            <Tooltip
              title={
                isRunning
                  ? t('runNow.running')
                  : !row.isActive
                    ? t('runNow.inactive')
                    : t('runNow.run')
              }
            >
              <span>
                <IconButton
                  size="small"
                  color="primary"
                  disabled={isRunning || !row.isActive}
                  onClick={() => handleRunNow(row)}
                >
                  {isRunning ? (
                    <CircularProgress size={18} />
                  ) : (
                    <RocketLaunchIcon />
                  )}
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title={row.isActive ? t('common:actions.pause') : t('common:actions.resume')}>
              <IconButton
                size="small"
                onClick={() => handleToggleActive(row)}
                color={row.isActive ? 'warning' : 'success'}
              >
                {row.isActive ? <PauseIcon /> : <PlayArrowIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title={t('common:actions.edit')}>
              <IconButton size="small" onClick={() => handleOpenEdit(row)}>
                <EditIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title={t('common:actions.delete')}>
              <IconButton
                size="small"
                color="error"
                onClick={() => setDeleteId(row.id)}
              >
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        )
      },
    },
  ]

  const selectedCount =
    rowSelection.type === 'include' ? rowSelection.ids.size : 0

  return (
    <Box>
      <PageHeader
        title={t('title')}
        actionLabel={t('new')}
        onAction={handleOpenCreate}
      />

      {selectedCount > 0 && (
        <Box sx={{ mb: 2 }}>
          <Chip
            label={t('common:selection.selected', { count: selectedCount })}
            onDelete={() =>
              setRowSelection({ type: 'include', ids: new Set() })
            }
            sx={{ mr: 1 }}
          />
          <Chip
            label={t('common:actions.deleteSelected')}
            color="error"
            variant="outlined"
            onClick={() => setBulkDeleteOpen(true)}
            icon={<DeleteIcon />}
          />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <DataGrid
        rows={items}
        columns={columns}
        loading={loading}
        rowCount={total}
        paginationMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        pageSizeOptions={[5, 10, 25]}
        checkboxSelection
        rowSelectionModel={rowSelection}
        onRowSelectionModelChange={setRowSelection}
        disableRowSelectionOnClick
        autoHeight
        sx={{ minHeight: 400 }}
        slots={{
          noRowsOverlay: () => (
            <Stack
              alignItems="center"
              justifyContent="center"
              sx={{ height: '100%', py: 6 }}
            >
              <NotificationsActiveIcon
                sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }}
              />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                {t('empty.title')}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 2 }}
              >
                {t('empty.body', { button: t('new') })}
              </Typography>
            </Stack>
          ),
        }}
      />

      {/* Create modal */}
      <GenericFormModal
        open={createOpen}
        title={t('dialogs.createTitle')}
        onClose={() => setCreateOpen(false)}
        onSave={handleCreate}
        saveLabel={t('common:actions.create')}
      >
        {formFields}
      </GenericFormModal>

      {/* Edit modal */}
      <GenericFormModal
        open={!!editAlert}
        title={t('dialogs.editTitle')}
        onClose={() => setEditAlert(null)}
        onSave={handleUpdate}
        saveLabel={t('common:actions.save')}
      >
        {formFields}
      </GenericFormModal>

      {/* Single delete */}
      <ConfirmationDialog
        open={!!deleteId}
        title={t('dialogs.deleteTitle')}
        message={`${t('dialogs.deleteMessage')} ${t('common:irreversible')}`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />

      {/* Bulk delete */}
      <ConfirmationDialog
        open={bulkDeleteOpen}
        title={t('dialogs.bulkDeleteTitle')}
        message={`${t('dialogs.bulkDeleteMessage', { count: selectedCount })} ${t('common:irreversible')}`}
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkDeleteOpen(false)}
      />
    </Box>
  )
}
