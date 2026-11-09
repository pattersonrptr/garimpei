/**
 * Products list page — MUI DataGrid with server-side pagination, sort and
 * filters. Customers see the listings their alerts found; staff see the whole
 * catalog and can edit or delete listings (one by one or in bulk).
 */

import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import FilterListIcon from '@mui/icons-material/FilterList'
import InventoryIcon from '@mui/icons-material/Inventory'
import VisibilityIcon from '@mui/icons-material/Visibility'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Checkbox from '@mui/material/Checkbox'
import Chip from '@mui/material/Chip'
import Collapse from '@mui/material/Collapse'
import FormControl from '@mui/material/FormControl'
import FormControlLabel from '@mui/material/FormControlLabel'
import IconButton from '@mui/material/IconButton'
import InputLabel from '@mui/material/InputLabel'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import {
  DataGrid,
  type GridColDef,
  type GridSortModel,
  type GridPaginationModel,
  type GridRowSelectionModel,
} from '@mui/x-data-grid'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog'
import { GenericFormModal } from '@/components/common/GenericFormModal'
import { PageHeader } from '@/components/common/PageHeader'
import { useAuth } from '@/context/AuthContext'
import { usePaginatedResource } from '@/hooks/usePaginatedResource'
import { matchesForProduct } from '@/lib/alertMatch'
import { formatCurrency } from '@/lib/formatters'
import { logger } from '@/lib/logger'
import { EMPTY_SELECTION, selectedRowIds } from '@/lib/selection'
import { deleteProduct, getProducts, updateProduct } from '@/services/productService'
import { getPriceAlertsByUser } from '@/services/priceAlertService'
import type { PriceAlert } from '@/types/priceAlert'
import type { Product, ProductCondition, ProductUpdatePayload } from '@/types/product'

// ---------------------------------------------------------------------------
// Filter state
// ---------------------------------------------------------------------------

interface Filters {
  title: string
  condition: string
  isAvailable: string
  opportunitiesOnly: boolean
}

const defaultFilters: Filters = {
  title: '',
  condition: '',
  isAvailable: '',
  opportunitiesOnly: false,
}

// ---------------------------------------------------------------------------
// Edit form state
// ---------------------------------------------------------------------------

interface EditFormState {
  title: string
  url: string
  condition: ProductCondition
  isAvailable: boolean
  description: string
  sellerName: string
}

const CONDITIONS: ProductCondition[] = ['new', 'used', 'refurbished', 'undetermined']

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ProductsPage() {
  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()
  const { t } = useTranslation(['products', 'common'])
  const { userId, isStaff, isSuperuser } = useAuth()
  const canManage = isStaff || isSuperuser

  // My alerts, to tag the listings that are opportunities for me
  const [alerts, setAlerts] = useState<PriceAlert[]>([])
  useEffect(() => {
    if (userId) {
      getPriceAlertsByUser(userId).then(setAlerts).catch(() => {})
    }
  }, [userId])

  /** Same rule as the API: one of my alerts matches and the price fits. */
  const isOpportunity = useCallback(
    (product: Product): boolean =>
      matchesForProduct(alerts, product).some((m) => m.isOpportunity),
    [alerts],
  )

  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({
    page: 0,
    pageSize: 10,
  })
  const [sortModel, setSortModel] = useState<GridSortModel>([])
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [showFilters, setShowFilters] = useState(false)
  const [rowSelection, setRowSelection] = useState<GridRowSelectionModel>(EMPTY_SELECTION)

  // Single delete
  const [deleteId, setDeleteId] = useState<string | null>(null)
  // Bulk delete
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false)

  // Edit modal
  const [editProduct, setEditProduct] = useState<Product | null>(null)
  const [editForm, setEditForm] = useState<EditFormState>({
    title: '',
    url: '',
    condition: 'undetermined',
    isAvailable: true,
    description: '',
    sellerName: '',
  })
  const [saving, setSaving] = useState(false)

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const fetcher = useCallback(
    () =>
      getProducts({
        limit: paginationModel.pageSize,
        offset: paginationModel.page * paginationModel.pageSize,
        sort_by: sortModel[0]?.field,
        sort_order: sortModel[0]?.sort ?? undefined,
        ...(filters.title ? { title: filters.title } : {}),
        ...(filters.condition ? { condition: filters.condition } : {}),
        ...(filters.isAvailable !== ''
          ? { is_available: filters.isAvailable === 'true' }
          : {}),
        ...(filters.opportunitiesOnly ? { opportunities_only: true } : {}),
      }),
    [paginationModel, sortModel, filters],
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

  function openEdit(product: Product) {
    setEditProduct(product)
    setEditForm({
      title: product.title,
      url: product.url,
      condition: product.condition,
      isAvailable: product.isAvailable,
      description: product.description ?? '',
      sellerName: product.sellerName ?? '',
    })
  }

  function applyFilters(next: Partial<Filters>) {
    setFilters((prev) => ({ ...prev, ...next }))
    setPaginationModel((prev) => ({ ...prev, page: 0 }))
  }

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  async function handleDelete() {
    if (!deleteId) return
    try {
      await deleteProduct(deleteId)
      enqueueSnackbar(t('toast.deleted'), { variant: 'success' })
      reload()
    } catch (err) {
      logger.error('Failed to delete product', { id: deleteId }, err)
      enqueueSnackbar(t('toast.deleteFailed'), { variant: 'error' })
    } finally {
      setDeleteId(null)
    }
  }

  async function handleBulkDelete() {
    setBulkDeleteOpen(false)
    const ids = selectedIds()
    try {
      await Promise.all(ids.map(deleteProduct))
      enqueueSnackbar(t('toast.bulkDeleted', { count: ids.length }), { variant: 'success' })
      setRowSelection(EMPTY_SELECTION)
      reload()
    } catch (err) {
      logger.error('Failed to bulk delete products', { ids }, err)
      enqueueSnackbar(t('toast.bulkDeleteFailed'), { variant: 'error' })
    }
  }

  async function handleEdit() {
    if (!editProduct) return
    setSaving(true)
    try {
      const payload: ProductUpdatePayload = {
        title: editForm.title || undefined,
        url: editForm.url || undefined,
        condition: editForm.condition,
        isAvailable: editForm.isAvailable,
        description: editForm.description || undefined,
        sellerName: editForm.sellerName || undefined,
      }
      await updateProduct(editProduct.id, payload)
      enqueueSnackbar(t('toast.updated'), { variant: 'success' })
      setEditProduct(null)
      reload()
    } catch (err) {
      logger.error('Failed to update product', { id: editProduct.id }, err)
      enqueueSnackbar(t('toast.updateFailed'), { variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Columns
  // ---------------------------------------------------------------------------

  const columns: GridColDef<Product>[] = [
    {
      field: 'title',
      headerName: t('fields.title'),
      flex: 2,
      minWidth: 200,
      renderCell: ({ row }) => (
        <Stack direction="row" spacing={1} alignItems="center">
          <span>{row.title}</span>
          {isOpportunity(row) && (
            <Chip
              size="small"
              label={t('opportunity')}
              color="success"
              variant="outlined"
              sx={{ height: 22, fontSize: '0.7rem' }}
            />
          )}
        </Stack>
      ),
    },
    {
      field: 'currentPrice',
      headerName: t('fields.currentPrice'),
      width: 140,
      valueFormatter: (value: number | undefined) =>
        value != null ? formatCurrency(value) : '—',
    },
    {
      field: 'condition',
      headerName: t('fields.condition'),
      width: 140,
      valueFormatter: (value: ProductCondition) => t(`condition.${value}`),
    },
    {
      field: 'isAvailable',
      headerName: t('fields.available'),
      width: 110,
      renderCell: ({ value }) => (
        <Chip
          label={value ? t('common:yesNo.yes') : t('common:yesNo.no')}
          color={value ? 'success' : 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: t('common:columns.actions'),
      width: 120,
      getActions: ({ row }) => [
        <Tooltip title={t('common:actions.viewDetails')} key="view">
          <IconButton
            size="small"
            aria-label={t('common:actions.viewDetails')}
            onClick={() => navigate(`/products/${row.id}`)}
          >
            <VisibilityIcon fontSize="small" />
          </IconButton>
        </Tooltip>,
        ...(canManage
          ? [
              <Tooltip title={t('common:actions.edit')} key="edit">
                <IconButton
                  size="small"
                  aria-label={t('common:actions.edit')}
                  onClick={() => openEdit(row)}
                >
                  <EditIcon fontSize="small" />
                </IconButton>
              </Tooltip>,
              <Tooltip title={t('common:actions.delete')} key="delete">
                <IconButton
                  size="small"
                  color="error"
                  aria-label={t('common:actions.delete')}
                  onClick={() => setDeleteId(row.id)}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Tooltip>,
            ]
          : []),
      ],
    },
  ]

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Box>
      <PageHeader title={t('title')} />

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* ── Toolbar ──────────────────────────────────────────────────── */}
      <Stack direction="row" spacing={1} sx={{ mb: 1 }} alignItems="center">
        <Button
          variant={showFilters ? 'contained' : 'outlined'}
          startIcon={<FilterListIcon />}
          onClick={() => setShowFilters((v) => !v)}
          size="small"
        >
          {t('common:filters.title')}
        </Button>
        <FormControlLabel
          control={
            <Checkbox
              size="small"
              checked={filters.opportunitiesOnly}
              onChange={(e) => applyFilters({ opportunitiesOnly: e.target.checked })}
            />
          }
          label={t('opportunitiesOnly')}
        />
        {canManage && selectionCount() > 0 && (
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon />}
            size="small"
            onClick={() => setBulkDeleteOpen(true)}
          >
            {t('deleteSelected', { count: selectionCount() })}
          </Button>
        )}
      </Stack>

      {/* ── Filter toolbar ────────────────────────────────────────────── */}
      <Collapse in={showFilters}>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }} flexWrap="wrap">
          <TextField
            label={t('fields.title')}
            size="small"
            value={filters.title}
            onChange={(e) => applyFilters({ title: e.target.value })}
            sx={{ minWidth: 200 }}
          />
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>{t('fields.condition')}</InputLabel>
            <Select
              label={t('fields.condition')}
              value={filters.condition}
              onChange={(e) => applyFilters({ condition: e.target.value })}
            >
              <MenuItem value="">{t('common:filters.all')}</MenuItem>
              {CONDITIONS.map((c) => (
                <MenuItem key={c} value={c}>
                  {t(`condition.${c}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>{t('fields.available')}</InputLabel>
            <Select
              label={t('fields.available')}
              value={filters.isAvailable}
              onChange={(e) => applyFilters({ isAvailable: e.target.value })}
            >
              <MenuItem value="">{t('common:filters.all')}</MenuItem>
              <MenuItem value="true">{t('common:yesNo.yes')}</MenuItem>
              <MenuItem value="false">{t('common:yesNo.no')}</MenuItem>
            </Select>
          </FormControl>
          <Button
            size="small"
            onClick={() => {
              setFilters(defaultFilters)
              setPaginationModel((prev) => ({ ...prev, page: 0 }))
            }}
          >
            {t('common:actions.clear')}
          </Button>
        </Stack>
      </Collapse>

      {/* ── Data grid ────────────────────────────────────────────────── */}
      <DataGrid
        rows={items}
        columns={columns}
        rowCount={total}
        loading={loading}
        paginationMode="server"
        sortingMode="server"
        paginationModel={paginationModel}
        onPaginationModelChange={setPaginationModel}
        sortModel={sortModel}
        onSortModelChange={setSortModel}
        pageSizeOptions={[10, 25, 50, 100]}
        checkboxSelection={canManage}
        rowSelectionModel={rowSelection}
        onRowSelectionModelChange={setRowSelection}
        disableRowSelectionOnClick
        autoHeight
        slots={{
          noRowsOverlay: () => (
            <Stack
              alignItems="center"
              justifyContent="center"
              sx={{ height: '100%', py: 6 }}
            >
              <InventoryIcon
                sx={{ fontSize: 48, color: 'text.disabled', mb: 1 }}
              />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                {t('empty.title')}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {filters.opportunitiesOnly ? t('empty.noOpportunities') : t('empty.body')}
              </Typography>
            </Stack>
          ),
        }}
      />

      {/* ── Edit modal ───────────────────────────────────────────────── */}
      <GenericFormModal
        open={editProduct !== null}
        title={t('dialogs.editTitle', { title: editProduct?.title ?? '' })}
        onClose={() => setEditProduct(null)}
        onSave={handleEdit}
        saving={saving}
      >
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField
            label={t('fields.title')}
            value={editForm.title}
            onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
            fullWidth
            size="small"
          />
          <TextField
            label={t('fields.url')}
            value={editForm.url}
            onChange={(e) => setEditForm((f) => ({ ...f, url: e.target.value }))}
            fullWidth
            size="small"
          />
          <FormControl size="small" fullWidth>
            <InputLabel>{t('fields.condition')}</InputLabel>
            <Select
              label={t('fields.condition')}
              value={editForm.condition}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, condition: e.target.value as ProductCondition }))
              }
            >
              {CONDITIONS.map((c) => (
                <MenuItem key={c} value={c}>
                  {t(`condition.${c}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" fullWidth>
            <InputLabel>{t('fields.available')}</InputLabel>
            <Select
              label={t('fields.available')}
              value={editForm.isAvailable ? 'true' : 'false'}
              onChange={(e) =>
                setEditForm((f) => ({ ...f, isAvailable: e.target.value === 'true' }))
              }
            >
              <MenuItem value="true">{t('common:yesNo.yes')}</MenuItem>
              <MenuItem value="false">{t('common:yesNo.no')}</MenuItem>
            </Select>
          </FormControl>
          <TextField
            label={t('fields.seller')}
            value={editForm.sellerName}
            onChange={(e) => setEditForm((f) => ({ ...f, sellerName: e.target.value }))}
            fullWidth
            size="small"
          />
          <TextField
            label={t('fields.description')}
            value={editForm.description}
            onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
            fullWidth
            multiline
            rows={3}
            size="small"
          />
        </Stack>
      </GenericFormModal>

      {/* ── Single delete confirmation ────────────────────────────────── */}
      <ConfirmationDialog
        open={!!deleteId}
        title={t('dialogs.deleteTitle')}
        message={`${t('dialogs.deleteMessage')} ${t('common:irreversible')}`}
        confirmLabel={t('common:actions.delete')}
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />

      {/* ── Bulk delete confirmation ──────────────────────────────────── */}
      <ConfirmationDialog
        open={bulkDeleteOpen}
        title={t('dialogs.bulkDeleteTitle')}
        message={`${t('dialogs.bulkDeleteMessage', { count: selectionCount() })} ${t('common:irreversible')}`}
        confirmLabel={t('common:actions.delete')}
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkDeleteOpen(false)}
      />
    </Box>
  )
}
