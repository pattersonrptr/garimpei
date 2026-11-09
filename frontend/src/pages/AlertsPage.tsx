/**
 * My Alerts page — PriceAlert CRUD with DataGrid, create/edit modal,
 * pause/resume toggle, "Run now" with live progress, and delete.
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
import FormHelperText from '@mui/material/FormHelperText'
import IconButton from '@mui/material/IconButton'
import InputAdornment from '@mui/material/InputAdornment'
import InputLabel from '@mui/material/InputLabel'
import Link from '@mui/material/Link'
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
import { Link as RouterLink } from 'react-router-dom'
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog'
import { GenericFormModal } from '@/components/common/GenericFormModal'
import { PageHeader } from '@/components/common/PageHeader'
import { useAuth } from '@/context/AuthContext'
import { usePaginatedResource } from '@/hooks/usePaginatedResource'
import { firstApiError, planLimitMessage } from '@/lib/apiErrors'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { logger } from '@/lib/logger'
import { EMPTY_SELECTION, selectedRowIds } from '@/lib/selection'
import { sourceDisplayName } from '@/lib/sources'
import {
  createPriceAlert,
  deletePriceAlert,
  getPriceAlerts,
  updatePriceAlert,
} from '@/services/priceAlertService'
import {
  getExecutionStatus,
  triggerSearchConfig,
  type ExecutionStatus,
} from '@/services/searchConfigService'
import { getAllSourceWebsites } from '@/services/sourceWebsiteService'
import { getMyLimits } from '@/services/subscriptionService'
import type { PlanLimits } from '@/types/plan'
import type { PriceAlert, PriceAlertCreatePayload } from '@/types/priceAlert'
import type { SourceWebsite } from '@/types/sourceWebsite'

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface FormState {
  searchTerm: string
  maxPrice: string
  frequencyMinutes: string
  isActive: boolean
  sourceWebsiteIds: number[]
}

/** Free plan default, used until the user's limits are loaded. */
const DEFAULT_MIN_FREQUENCY = 360
const POLL_INTERVAL_MS = 3000

function emptyForm(minFrequency: number): FormState {
  return {
    searchTerm: '',
    maxPrice: '',
    frequencyMinutes: String(minFrequency),
    isActive: true,
    sourceWebsiteIds: [],
  }
}

/** Last known state of a manual run, per search config id. */
type RunState = { status: 'pending' } | ExecutionStatus

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AlertsPage() {
  const { enqueueSnackbar } = useSnackbar()
  const { userId } = useAuth()
  const { t } = useTranslation(['alerts', 'common'])
  const { t: tc } = useTranslation('common')

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })
  const [rowSelection, setRowSelection] = useState<GridRowSelectionModel>(EMPTY_SELECTION)

  // CRUD state
  const [createOpen, setCreateOpen] = useState(false)
  const [editAlert, setEditAlert] = useState<PriceAlert | null>(null)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)
  const [limits, setLimits] = useState<PlanLimits | null>(null)
  const minFrequency = limits?.minFrequencyMinutes ?? DEFAULT_MIN_FREQUENCY
  const [form, setForm] = useState<FormState>(() => emptyForm(DEFAULT_MIN_FREQUENCY))
  /** Why the API refused the form (plan limits), shown inside the dialog. */
  const [formError, setFormError] = useState<string | null>(null)

  const [sourceWebsites, setSourceWebsites] = useState<SourceWebsite[]>([])

  // Run now: progress per search config, and the timers polling it
  const [runs, setRuns] = useState<Record<string, RunState>>({})
  const pollingTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({})
  /** Latest watchRun, for the effect that resumes runs on load (defined above it). */
  const watchRunRef = useRef<(key: string) => void>(() => {})

  // Last finished check per search config
  const [lastCheckMap, setLastCheckMap] = useState<Record<string, string>>({})

  useEffect(() => {
    const timers = pollingTimers.current
    return () => {
      Object.values(timers).forEach(clearInterval)
    }
  }, [])

  useEffect(() => {
    getAllSourceWebsites().then(setSourceWebsites).catch(() => {})
    getMyLimits().then(setLimits).catch(() => {})
  }, [])

  const { items, total, loading, error, setPagination, reload } =
    usePaginatedResource(getPriceAlerts)

  // Last check of every search config in the list
  useEffect(() => {
    if (!items.length) return
    const uniqueIds = [
      ...new Set(items.map((a) => a.searchConfigId).filter((id): id is number => id != null)),
    ]
    Promise.allSettled(
      uniqueIds.map((id) => getExecutionStatus(String(id)).then((es) => ({ id, es }))),
    ).then((results) => {
      const map: Record<string, string> = {}
      for (const r of results) {
        if (r.status !== 'fulfilled') continue
        const { id, es } = r.value
        if (es.status === 'pending' || es.status === 'running') {
          // A run started earlier (here, in another tab or by the schedule)
          setRuns((prev) => ({ ...prev, [String(id)]: es }))
          watchRunRef.current(String(id))
        }
        const when = es.finishedAt ?? (es.status === 'success' || es.status === 'failed' ? es.startedAt : null)
        if (when) map[String(id)] = when
      }
      setLastCheckMap((prev) => ({ ...prev, ...map }))
    })
  }, [items])

  useEffect(() => {
    setPagination({ page: paginationModel.page, pageSize: paginationModel.pageSize })
  }, [paginationModel, setPagination])

  const handleOpenCreate = useCallback(() => {
    setForm(emptyForm(minFrequency))
    setFormError(null)
    setCreateOpen(true)
  }, [minFrequency])

  const handleOpenEdit = useCallback((alert: PriceAlert) => {
    setForm({
      searchTerm: alert.searchTerm,
      maxPrice: String(alert.maxPrice),
      frequencyMinutes: String(alert.frequencyMinutes),
      isActive: alert.isActive,
      sourceWebsiteIds: alert.sourceWebsiteIds,
    })
    setFormError(null)
    setEditAlert(alert)
  }, [])

  /** Plan limits are explained inside the form; anything else is a toast. */
  const showSaveError = useCallback(
    (err: unknown, fallback: string) => {
      const planMessage = planLimitMessage(err, tc)
      if (planMessage) {
        setFormError(planMessage)
      } else {
        enqueueSnackbar(fallback, { variant: 'error' })
      }
    },
    [enqueueSnackbar, tc],
  )

  const handleCreate = useCallback(async () => {
    if (!userId) return
    setFormError(null)
    try {
      const payload: PriceAlertCreatePayload = {
        searchTerm: form.searchTerm.trim(),
        maxPrice: parseFloat(form.maxPrice),
        userId,
        isActive: form.isActive,
        frequencyMinutes: parseInt(form.frequencyMinutes, 10) || 0,
        sourceWebsiteIds: form.sourceWebsiteIds,
      }
      await createPriceAlert(payload)
      enqueueSnackbar(t('toast.created'), { variant: 'success' })
      setCreateOpen(false)
      reload()
    } catch (err) {
      logger.error('Failed to create alert', {}, err)
      showSaveError(err, t('toast.createFailed'))
    }
  }, [form, userId, enqueueSnackbar, reload, t, showSaveError])

  const handleUpdate = useCallback(async () => {
    if (!editAlert) return
    setFormError(null)
    try {
      await updatePriceAlert(editAlert.id, {
        searchTerm: form.searchTerm.trim(),
        maxPrice: parseFloat(form.maxPrice),
        isActive: form.isActive,
        frequencyMinutes: parseInt(form.frequencyMinutes, 10) || 0,
        sourceWebsiteIds: form.sourceWebsiteIds,
      })
      enqueueSnackbar(t('toast.updated'), { variant: 'success' })
      setEditAlert(null)
      reload()
    } catch (err) {
      logger.error('Failed to update alert', {}, err)
      showSaveError(err, t('toast.updateFailed'))
    }
  }, [editAlert, form, enqueueSnackbar, reload, t, showSaveError])

  const handleToggleActive = useCallback(
    async (alert: PriceAlert) => {
      try {
        await updatePriceAlert(alert.id, { isActive: !alert.isActive })
        enqueueSnackbar(alert.isActive ? t('toast.paused') : t('toast.resumed'), {
          variant: 'info',
        })
        reload()
      } catch (err) {
        logger.error('Failed to toggle alert', {}, err)
        enqueueSnackbar(planLimitMessage(err, tc) ?? t('toast.updateFailed'), {
          variant: 'error',
        })
      }
    },
    [enqueueSnackbar, reload, t, tc],
  )

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

  const selectedIds = selectedRowIds(rowSelection, items)

  const handleBulkDelete = useCallback(async () => {
    const ids = selectedRowIds(rowSelection, items)
    try {
      await Promise.all(ids.map(deletePriceAlert))
      enqueueSnackbar(t('toast.bulkDeleted', { count: ids.length }), { variant: 'success' })
      setBulkDeleteOpen(false)
      setRowSelection(EMPTY_SELECTION)
      reload()
    } catch (err) {
      logger.error('Bulk delete failed', {}, err)
      enqueueSnackbar(t('toast.bulkDeleteFailed'), { variant: 'error' })
    }
  }, [rowSelection, items, enqueueSnackbar, reload, t])

  // -------------------------------------------------------------------------
  // Run now: trigger, then poll the run until it finishes
  // -------------------------------------------------------------------------

  const stopPolling = useCallback((scId: string) => {
    clearInterval(pollingTimers.current[scId])
    delete pollingTimers.current[scId]
    setRuns((prev) => {
      const next = { ...prev }
      delete next[scId]
      return next
    })
  }, [])

  const announceFinishedRun = useCallback(
    (run: ExecutionStatus) => {
      if (run.status === 'failed') {
        enqueueSnackbar(
          t('runNow.failed', { error: run.errorMessage ?? tc('status.unknownError') }),
          { variant: 'error' },
        )
      } else if (!run.listingsFound && !run.listingsChecked) {
        enqueueSnackbar(t('runNow.nothingFound'), { variant: 'warning' })
      } else {
        const checked = run.listingsChecked ?? 0
        const matched = run.resultsCount ?? 0
        enqueueSnackbar(
          t('runNow.done', {
            count: checked,
            matches: t('runNow.matches', { count: matched }),
          }),
          { variant: 'success', autoHideDuration: 10000 },
        )
      }
    },
    [enqueueSnackbar, t, tc],
  )

  /** Poll a search run until it finishes, then announce the result. */
  const watchRun = useCallback(
    (key: string) => {
      if (pollingTimers.current[key]) return
      pollingTimers.current[key] = setInterval(async () => {
        try {
          const run = await getExecutionStatus(key)
          if (run.status === 'success' || run.status === 'failed') {
            stopPolling(key)
            const when = run.finishedAt ?? run.startedAt
            if (when) setLastCheckMap((prev) => ({ ...prev, [key]: when }))
            announceFinishedRun(run)
            reload()
          } else {
            setRuns((prev) => ({ ...prev, [key]: run }))
          }
        } catch {
          // a failed poll is retried on the next tick
        }
      }, POLL_INTERVAL_MS)
    },
    [stopPolling, announceFinishedRun, reload],
  )
  useEffect(() => {
    watchRunRef.current = watchRun
  }, [watchRun])

  const handleRunNow = useCallback(
    async (alert: PriceAlert) => {
      const scId = alert.searchConfigId
      if (!scId) {
        enqueueSnackbar(t('runNow.noConfig'), { variant: 'warning' })
        return
      }
      const key = String(scId)
      setRuns((prev) => ({ ...prev, [key]: { status: 'pending' } }))

      try {
        await triggerSearchConfig(key)
        enqueueSnackbar(t('runNow.triggered'), { variant: 'info' })
        watchRun(key)
      } catch (err) {
        stopPolling(key)
        const { status } = firstApiError(err)
        if (status === 409) {
          enqueueSnackbar(t('runNow.alreadyRunning'), { variant: 'warning' })
          return
        }
        const planMessage = planLimitMessage(err, tc)
        enqueueSnackbar(planMessage ?? t('runNow.triggerFailed'), {
          variant: planMessage ? 'warning' : 'error',
        })
      }
    },
    [enqueueSnackbar, t, tc, stopPolling, watchRun],
  )

  const sourceName = useCallback(
    (id: number) => {
      const site = sourceWebsites.find((s) => String(s.id) === String(id))
      return site ? sourceDisplayName(site.name) : `#${id}`
    },
    [sourceWebsites],
  )

  /** What the "last check" cell says while a run is in progress. */
  const runProgress = (run: RunState): string => {
    if ('listingsFound' in run && run.listingsFound) {
      return t('runNow.progress', {
        checked: run.listingsChecked ?? 0,
        count: run.listingsFound,
      })
    }
    return t('runNow.searching')
  }

  // -------------------------------------------------------------------------
  // Form
  // -------------------------------------------------------------------------

  // Plan names come lowercase from the API ("free"); shown as a name ("Free")
  const rawPlanName = limits?.planName ?? 'free'
  const planName = rawPlanName.charAt(0).toUpperCase() + rawPlanName.slice(1)
  const sourcesLabelId = 'alert-sources-label'

  const formFields = (
    <Stack spacing={2} sx={{ mt: 1 }}>
      {formError && (
        <Alert severity="warning">
          {formError}{' '}
          <Link component={RouterLink} to="/plans">
            {t('seePlans')}
          </Link>
        </Alert>
      )}
      <TextField
        label={t('fields.searchTerm')}
        fullWidth
        required
        value={form.searchTerm}
        helperText={t('help.searchTerm')}
        onChange={(e) => setForm((f) => ({ ...f, searchTerm: e.target.value }))}
      />
      <TextField
        label={t('fields.maxPrice')}
        fullWidth
        required
        type="number"
        helperText={t('help.maxPrice')}
        slotProps={{
          input: {
            startAdornment: <InputAdornment position="start">R$</InputAdornment>,
          },
        }}
        value={form.maxPrice}
        onChange={(e) => setForm((f) => ({ ...f, maxPrice: e.target.value }))}
      />
      <TextField
        label={t('fields.frequency')}
        fullWidth
        type="number"
        helperText={t('help.frequency', { plan: planName, count: minFrequency })}
        slotProps={{ htmlInput: { min: minFrequency, step: 30 } }}
        value={form.frequencyMinutes}
        onChange={(e) => setForm((f) => ({ ...f, frequencyMinutes: e.target.value }))}
      />
      <FormControl fullWidth>
        <InputLabel id={sourcesLabelId}>{t('fields.sources')}</InputLabel>
        <Select
          multiple
          labelId={sourcesLabelId}
          value={form.sourceWebsiteIds}
          onChange={(e) => {
            const val = e.target.value
            setForm((f) => ({
              ...f,
              sourceWebsiteIds:
                typeof val === 'string' ? val.split(',').map(Number) : (val as number[]),
            }))
          }}
          input={<OutlinedInput label={t('fields.sources')} />}
          renderValue={(selected) => selected.map((id) => sourceName(id)).join(', ')}
        >
          {sourceWebsites
            .filter((sw) => sw.isActive)
            .map((sw) => (
              <MenuItem key={sw.id} value={Number(sw.id)}>
                <ListItemText primary={sourceDisplayName(sw.name)} />
              </MenuItem>
            ))}
        </Select>
        {limits?.maxSources != null && (
          <FormHelperText>{t('help.sources', { count: limits.maxSources })}</FormHelperText>
        )}
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

  // -------------------------------------------------------------------------
  // Grid
  // -------------------------------------------------------------------------

  const columns: GridColDef<PriceAlert>[] = [
    { field: 'searchTerm', headerName: t('columns.keyword'), flex: 1, minWidth: 150 },
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
          label={value ? tc('status.active') : tc('status.paused')}
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
          <Stack direction="row" spacing={0.5} flexWrap="wrap" alignItems="center" sx={{ height: '100%' }}>
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
      renderCell: ({ value }) => tc('units.minutes', { count: value }),
    },
    {
      field: 'lastTriggeredAt',
      headerName: t('columns.lastCheck'),
      width: 220,
      renderCell: ({ row }) => {
        const scId = row.searchConfigId ? String(row.searchConfigId) : null
        const run = scId ? runs[scId] : undefined
        if (run) {
          return (
            <Typography variant="body2" color="primary" sx={{ lineHeight: 'inherit' }}>
              {runProgress(run)}
            </Typography>
          )
        }
        const ts = scId ? lastCheckMap[scId] : null
        return ts ? formatDateTime(ts) : tc('status.never')
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
        const isRunning = scId ? scId in runs : false
        const pauseLabel = row.isActive ? tc('actions.pause') : tc('actions.resume')
        return (
          <Stack direction="row" spacing={0.5}>
            <Tooltip title={isRunning ? t('runNow.running') : t('runNow.hint')}>
              <span>
                <IconButton
                  size="small"
                  color="primary"
                  aria-label={t('runNow.run')}
                  disabled={isRunning}
                  onClick={() => handleRunNow(row)}
                >
                  {isRunning ? <CircularProgress size={18} /> : <RocketLaunchIcon />}
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title={pauseLabel}>
              <IconButton
                size="small"
                aria-label={pauseLabel}
                onClick={() => handleToggleActive(row)}
                color={row.isActive ? 'warning' : 'success'}
              >
                {row.isActive ? <PauseIcon /> : <PlayArrowIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title={tc('actions.edit')}>
              <IconButton size="small" aria-label={tc('actions.edit')} onClick={() => handleOpenEdit(row)}>
                <EditIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title={tc('actions.delete')}>
              <IconButton
                size="small"
                color="error"
                aria-label={tc('actions.delete')}
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

  const selectedCount = selectedIds.length

  return (
    <Box>
      <PageHeader title={t('title')} actionLabel={t('new')} onAction={handleOpenCreate} />

      {selectedCount > 0 && (
        <Box sx={{ mb: 2 }}>
          <Chip
            label={tc('selection.selected', { count: selectedCount })}
            onDelete={() => setRowSelection(EMPTY_SELECTION)}
            sx={{ mr: 1 }}
          />
          <Chip
            label={tc('actions.deleteSelected')}
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
            <Stack alignItems="center" justifyContent="center" sx={{ height: '100%', py: 6 }}>
              <NotificationsActiveIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                {t('empty.title')}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {t('empty.body', { button: t('new') })}
              </Typography>
            </Stack>
          ),
        }}
      />

      <GenericFormModal
        open={createOpen}
        title={t('dialogs.createTitle')}
        onClose={() => setCreateOpen(false)}
        onSave={handleCreate}
        saveLabel={tc('actions.create')}
      >
        {formFields}
      </GenericFormModal>

      <GenericFormModal
        open={!!editAlert}
        title={t('dialogs.editTitle')}
        onClose={() => setEditAlert(null)}
        onSave={handleUpdate}
        saveLabel={tc('actions.save')}
      >
        {formFields}
      </GenericFormModal>

      <ConfirmationDialog
        open={!!deleteId}
        title={t('dialogs.deleteTitle')}
        message={`${t('dialogs.deleteMessage')} ${tc('irreversible')}`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />

      <ConfirmationDialog
        open={bulkDeleteOpen}
        title={t('dialogs.bulkDeleteTitle')}
        message={`${t('dialogs.bulkDeleteMessage', { count: selectedCount })} ${tc('irreversible')}`}
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkDeleteOpen(false)}
      />
    </Box>
  )
}
