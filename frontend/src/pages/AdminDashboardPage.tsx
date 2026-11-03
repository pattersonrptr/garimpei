import { useEffect, useState } from 'react'

import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import GroupIcon from '@mui/icons-material/Group'
import InventoryIcon from '@mui/icons-material/Inventory'
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import WebIcon from '@mui/icons-material/Web'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Grid from '@mui/material/Grid'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Table from '@mui/material/Table'
import TableBody from '@mui/material/TableBody'
import TableCell from '@mui/material/TableCell'
import TableContainer from '@mui/material/TableContainer'
import TableHead from '@mui/material/TableHead'
import TableRow from '@mui/material/TableRow'
import Typography from '@mui/material/Typography'
import { useTranslation } from 'react-i18next'
import { formatShortDateTime } from '@/lib/formatters'
import {
  getAdminSummary,
  type AdminSummary,
  type ScraperExecution,
} from '@/services/adminService'

function StatCard({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string
  value: number
  subtitle?: string
  icon: React.ReactNode
}) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={2}>
          <Box sx={{ color: 'primary.main' }}>{icon}</Box>
          <Box>
            <Typography variant="h4" fontWeight={700}>
              {value}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="caption" color="text.disabled">
                {subtitle}
              </Typography>
            )}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  )
}

function StatusChip({ status }: { status: string }) {
  const { t } = useTranslation('admin')
  const color =
    status === 'success'
      ? 'success'
      : status === 'failed'
        ? 'error'
        : status === 'running'
          ? 'info'
          : 'default'
  return <Chip label={t(`dashboard.executionStatus.${status}`, { defaultValue: status })} color={color} size="small" variant="outlined" />
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return formatShortDateTime(iso)
}

export function AdminDashboardPage() {
  const { t } = useTranslation('admin')
  const [summary, setSummary] = useState<AdminSummary | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getAdminSummary()
      .then(setSummary)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" mt={8}>
        <CircularProgress />
      </Box>
    )
  }

  if (!summary) {
    return (
      <Typography color="error" mt={4}>
        {t('dashboard.loadFailed')}
      </Typography>
    )
  }

  const { scraperStats, recentExecutions } = summary

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} gutterBottom>
        {t('dashboard.title')}
      </Typography>

      {/* ── Summary cards ──────────────────────────────────────────── */}
      <Grid container spacing={3} mb={4}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title={t('dashboard.cards.users')}
            value={summary.totalUsers}
            subtitle={t('dashboard.cards.active', { count: summary.activeUsers })}
            icon={<GroupIcon fontSize="large" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title={t('dashboard.cards.alerts')}
            value={summary.totalAlerts}
            subtitle={t('dashboard.cards.active', { count: summary.activeAlerts })}
            icon={<NotificationsActiveIcon fontSize="large" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title={t('dashboard.cards.products')}
            value={summary.totalProducts}
            icon={<InventoryIcon fontSize="large" />}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title={t('dashboard.cards.websites')}
            value={summary.totalSourceWebsites}
            subtitle={t('dashboard.cards.active', { count: summary.activeSourceWebsites })}
            icon={<WebIcon fontSize="large" />}
          />
        </Grid>
      </Grid>

      {/* ── Scraper stats ──────────────────────────────────────────── */}
      <Grid container spacing={3} mb={4}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              {t('dashboard.scrapers.title')}
            </Typography>
            <Stack direction="row" spacing={4} alignItems="center">
              <Stack alignItems="center">
                <Typography variant="h3" fontWeight={700} color="success.main">
                  {scraperStats.successCount}
                </Typography>
                <Stack direction="row" alignItems="center" spacing={0.5}>
                  <CheckCircleIcon fontSize="small" color="success" />
                  <Typography variant="body2" color="text.secondary">
                    {t('dashboard.scrapers.success')}
                  </Typography>
                </Stack>
              </Stack>
              <Stack alignItems="center">
                <Typography variant="h3" fontWeight={700} color="error.main">
                  {scraperStats.failedCount}
                </Typography>
                <Stack direction="row" alignItems="center" spacing={0.5}>
                  <ErrorIcon fontSize="small" color="error" />
                  <Typography variant="body2" color="text.secondary">
                    {t('dashboard.scrapers.failed')}
                  </Typography>
                </Stack>
              </Stack>
              <Stack alignItems="center">
                <Typography variant="h3" fontWeight={700}>
                  {scraperStats.recentTotal}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('dashboard.scrapers.total')}
                </Typography>
              </Stack>
            </Stack>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            <Typography variant="h6" gutterBottom>
              {t('dashboard.monitoring.title')}
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={2}>
              {t('dashboard.monitoring.body')}
            </Typography>
            <Button
              variant="outlined"
              endIcon={<OpenInNewIcon />}
              href="http://localhost:5555"
              target="_blank"
              rel="noopener"
            >
              {t('dashboard.monitoring.open')}
            </Button>
          </Paper>
        </Grid>
      </Grid>

      {/* ── Recent executions table ────────────────────────────────── */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          {t('dashboard.executions.title')}
        </Typography>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>{t('dashboard.executions.configId')}</TableCell>
                <TableCell>{t('dashboard.executions.status')}</TableCell>
                <TableCell align="right">{t('dashboard.executions.results')}</TableCell>
                <TableCell>{t('dashboard.executions.started')}</TableCell>
                <TableCell>{t('dashboard.executions.error')}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {recentExecutions.map((exec: ScraperExecution) => (
                <TableRow key={exec.id}>
                  <TableCell>{exec.id}</TableCell>
                  <TableCell>{exec.searchConfigId}</TableCell>
                  <TableCell>
                    <StatusChip status={exec.status} />
                  </TableCell>
                  <TableCell align="right">
                    {exec.resultsCount ?? '—'}
                  </TableCell>
                  <TableCell>{formatDate(exec.startedAt)}</TableCell>
                  <TableCell>
                    {exec.errorMessage ? (
                      <Typography
                        variant="caption"
                        color="error"
                        sx={{ maxWidth: 200, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis' }}
                      >
                        {exec.errorMessage}
                      </Typography>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  )
}
