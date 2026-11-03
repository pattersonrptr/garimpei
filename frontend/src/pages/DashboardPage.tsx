/**
 * Dashboard page — landing page after login.
 *
 * Cards:
 *   1. Active Alerts — count + quick link to /alerts
 *   2. Recent Opportunities — products below target price
 *   3. Next Checks — when each alert is scheduled to run
 */

import AccessTimeIcon from '@mui/icons-material/AccessTime'
import AddAlertIcon from '@mui/icons-material/AddAlert'
import LocalOfferIcon from '@mui/icons-material/LocalOffer'
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import Link from '@mui/material/Link'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/common/PageHeader'
import { useAuth } from '@/context/AuthContext'
import { useDashboardSummary } from '@/hooks/useDashboardSummary'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import type { OpportunityProduct, AlertNextCheck } from '@/services/dashboardService'

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function OnboardingCard() {
  const navigate = useNavigate()
  const { t } = useTranslation('dashboard')

  return (
    <Paper
      elevation={0}
      sx={{
        p: 4,
        textAlign: 'center',
        border: '2px dashed',
        borderColor: 'primary.main',
        borderRadius: 2,
        bgcolor: 'primary.50',
        gridColumn: { md: '1 / -1' },
      }}
    >
      <AddAlertIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
      <Typography variant="h5" fontWeight={700} gutterBottom>
        {t('onboarding.title')}
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3, maxWidth: 480, mx: 'auto' }}>
        {t('onboarding.body')}
      </Typography>
      <Button
        variant="contained"
        size="large"
        startIcon={<AddAlertIcon />}
        onClick={() => navigate('/alerts')}
        sx={{ fontWeight: 700, px: 4 }}
      >
        {t('onboarding.button')}
      </Button>
    </Paper>
  )
}

function ActiveAlertsCard({
  active,
  total,
}: {
  active: number
  total: number
}) {
  const navigate = useNavigate()
  const { t } = useTranslation('dashboard')

  return (
    <Card
      sx={{
        cursor: 'pointer',
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 6 },
      }}
      onClick={() => navigate('/alerts')}
    >
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} mb={1}>
          <NotificationsActiveIcon color="primary" />
          <Typography variant="h6">{t('activeAlerts.title')}</Typography>
        </Stack>
        <Typography variant="h3" fontWeight="bold" color="primary">
          {active}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t('activeAlerts.total', { count: total })}
        </Typography>
      </CardContent>
    </Card>
  )
}

function OpportunitiesCard({
  opportunities,
}: {
  opportunities: OpportunityProduct[]
}) {
  const { t } = useTranslation('dashboard')

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} mb={1}>
          <TrendingDownIcon color="success" />
          <Typography variant="h6">{t('opportunities.title')}</Typography>
          <Chip
            size="small"
            label={opportunities.length}
            color="success"
            variant="outlined"
          />
        </Stack>

        {opportunities.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            {t('opportunities.empty')}
          </Typography>
        ) : (
          <List dense disablePadding>
            {opportunities.slice(0, 8).map((op) => (
              <ListItem
                key={`${op.alertId}-${op.id}`}
                disableGutters
                secondaryAction={
                  <Tooltip title={t('opportunities.openProduct')}>
                    <IconButton
                      edge="end"
                      size="small"
                      component="a"
                      href={op.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <OpenInNewIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                }
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <LocalOfferIcon fontSize="small" color="success" />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography variant="body2" noWrap sx={{ maxWidth: 300 }}>
                      {op.title}
                    </Typography>
                  }
                  secondary={
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography
                        component="span"
                        variant="body2"
                        fontWeight="bold"
                        color="success.main"
                      >
                        {formatCurrency(op.currentPrice)}
                      </Typography>
                      <Typography
                        component="span"
                        variant="caption"
                        color="text.secondary"
                      >
                        {t('opportunities.max', { price: formatCurrency(op.alertMaxPrice) })}
                      </Typography>
                      <Chip
                        size="small"
                        label={op.alertSearchTerm}
                        variant="outlined"
                        sx={{ height: 20, fontSize: '0.7rem' }}
                      />
                    </Stack>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  )
}

function NextChecksCard({ checks }: { checks: AlertNextCheck[] }) {
  const { t } = useTranslation('dashboard')

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1} mb={1}>
          <AccessTimeIcon color="info" />
          <Typography variant="h6">{t('nextChecks.title')}</Typography>
        </Stack>

        {checks.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            {t('nextChecks.empty')}
          </Typography>
        ) : (
          <List dense disablePadding>
            {checks.slice(0, 8).map((check) => (
              <ListItem key={check.alertId} disableGutters>
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <AccessTimeIcon fontSize="small" color="info" />
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography variant="body2" fontWeight="medium">
                      {check.searchTerm}
                    </Typography>
                  }
                  secondary={
                    check.nextCheckAt ? (
                      <Typography variant="caption" color="text.secondary">
                        {t('nextChecks.next', {
                          date: formatDateTime(check.nextCheckAt),
                          minutes: check.frequencyMinutes,
                        })}
                      </Typography>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        {t('nextChecks.notYet', { minutes: check.frequencyMinutes })}
                      </Typography>
                    )
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DashboardPage() {
  const { userId } = useAuth()
  const { summary, loading, error } = useDashboardSummary(userId)
  const { t } = useTranslation('dashboard')

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={300}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box>
        <PageHeader title={t('title')} />
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      </Box>
    )
  }

  if (!summary) {
    return (
      <Box>
        <PageHeader title={t('title')} />
        <Typography color="text.secondary">{t('noData')}</Typography>
      </Box>
    )
  }

  const isNewUser = summary.totalAlerts === 0

  return (
    <Box>
      <PageHeader title={t('title')} />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, mt: -2 }}>
        {t('subtitle')}
      </Typography>

      {isNewUser ? (
        <Box sx={{ mt: 2 }}>
          <OnboardingCard />
        </Box>
      ) : (
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              md: '1fr 1fr',
              lg: '300px 1fr 1fr',
            },
            gap: 3,
            mt: 2,
          }}
        >
          {/* Active Alerts card */}
          <ActiveAlertsCard
            active={summary.activeAlerts}
            total={summary.totalAlerts}
          />

          {/* Recent Opportunities */}
          <OpportunitiesCard opportunities={summary.recentOpportunities} />

          {/* Next Checks */}
          <NextChecksCard checks={summary.nextChecks} />
        </Box>
      )}

      <Divider sx={{ my: 4 }} />

      <Typography variant="body2" color="text.secondary">
        {t('tip.before')}
        <Link href="/alerts" variant="body2">
          {t('tip.link')}
        </Link>
        {t('tip.after')}
      </Typography>
    </Box>
  )
}
