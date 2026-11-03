/**
 * Plans page — pricing table showing Free, Pro, and Business tiers.
 * Users can view their current plan and subscribe/cancel.
 */

import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline'
import StarIcon from '@mui/icons-material/Star'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardActions from '@mui/material/CardActions'
import CardContent from '@mui/material/CardContent'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useCallback, useEffect, useState } from 'react'
import { useSnackbar } from 'notistack'
import { Trans, useTranslation } from 'react-i18next'
import { PageHeader } from '@/components/common/PageHeader'
import { formatCurrency } from '@/lib/formatters'
import { logger } from '@/lib/logger'
import { getPlans } from '@/services/planService'
import {
  getMySubscription,
  subscribeToPlan,
  cancelSubscription,
} from '@/services/subscriptionService'
import type { Plan, Subscription } from '@/types/plan'


interface FeatureRowProps {
  label: string
  value: string | boolean
}

function FeatureRow({ label, value }: FeatureRowProps) {
  const isBoolean = typeof value === 'boolean'
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ py: 0.5 }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      {isBoolean ? (
        value ? (
          <CheckCircleIcon fontSize="small" color="success" />
        ) : (
          <RemoveCircleOutlineIcon fontSize="small" color="disabled" />
        )
      ) : (
        <Typography variant="body2" fontWeight={600}>
          {value}
        </Typography>
      )}
    </Stack>
  )
}

export function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { enqueueSnackbar } = useSnackbar()
  const { t } = useTranslation(['plans', 'common'])

  const formatPrice = (cents: number) =>
    cents === 0 ? t('free') : formatCurrency(cents / 100)
  const formatLimit = (value: number | null) =>
    value === null ? t('unlimited') : String(value)
  const formatDays = (value: number | null) =>
    value === null ? t('unlimited') : t('days', { count: value })
  const formatFrequency = (minutes: number) =>
    minutes < 60
      ? t('common:units.minutes', { count: minutes })
      : t('hours', { count: minutes / 60 })

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [plansData, subData] = await Promise.all([
        getPlans(),
        getMySubscription(),
      ])
      setPlans(plansData)
      setSubscription(subData)
    } catch (err) {
      logger.error('Failed to load plans', {}, err)
      setError(t('loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSubscribe = async (planId: string) => {
    try {
      setActionLoading(planId)
      const newSub = await subscribeToPlan(planId)
      setSubscription(newSub)
      enqueueSnackbar(t('toast.subscribed'), { variant: 'success' })
    } catch (err) {
      logger.error('Failed to subscribe', {}, err)
      enqueueSnackbar(t('toast.subscribeFailed'), {
        variant: 'error',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCancel = async () => {
    try {
      setActionLoading('cancel')
      const updated = await cancelSubscription()
      setSubscription(updated)
      enqueueSnackbar(t('toast.canceled'), { variant: 'info' })
    } catch (err) {
      logger.error('Failed to cancel subscription', {}, err)
      enqueueSnackbar(t('toast.cancelFailed'), {
        variant: 'error',
      })
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">{error}</Alert>
      </Box>
    )
  }

  // Match by id: the API's planName is the display name ("Free"), not the slug
  const currentPlan =
    plans.find((p) => String(p.id) === String(subscription?.planId)) ??
    plans.find((p) => p.priceCents === 0)

  return (
    <Box p={3}>
      <PageHeader
        title={t('title')}
        subtitle={t('subtitle')}
      />

      {subscription && currentPlan && currentPlan.priceCents > 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Trans
            t={t}
            i18nKey="currentInfo"
            values={{ plan: currentPlan.displayName }}
            components={{ strong: <strong /> }}
          />
          {subscription.status === 'active' && t('status.active')}
          {subscription.status === 'canceled' && t('status.canceled')}
        </Alert>
      )}

      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={3}
        justifyContent="center"
        alignItems={{ xs: 'center', md: 'stretch' }}
      >
        {plans.map((plan) => {
          const isCurrent = currentPlan?.id === plan.id
          const isPopular = plan.name === 'pro'

          return (
            <Card
              key={plan.id}
              variant={isPopular ? 'elevation' : 'outlined'}
              sx={{
                width: { xs: '100%', md: 340 },
                position: 'relative',
                border: isPopular ? 2 : undefined,
                borderColor: isPopular ? 'primary.main' : undefined,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'visible', // keep the "most popular" badge uncut
              }}
              elevation={isPopular ? 8 : 1}
            >
              {isPopular && (
                <Chip
                  icon={<StarIcon />}
                  label={t('popular')}
                  color="primary"
                  size="small"
                  sx={{
                    position: 'absolute',
                    top: -12,
                    left: '50%',
                    transform: 'translateX(-50%)',
                  }}
                />
              )}

              <CardContent sx={{ flexGrow: 1, pt: isPopular ? 3 : 2 }}>
                <Typography variant="h5" fontWeight={700} gutterBottom>
                  {plan.displayName}
                </Typography>

                <Typography variant="h4" fontWeight={800} color="primary" gutterBottom>
                  {formatPrice(plan.priceCents)}
                  {plan.priceCents > 0 && (
                    <Typography component="span" variant="body2" color="text.secondary">
                      {t('perMonth')}
                    </Typography>
                  )}
                </Typography>

                <Stack spacing={0.5} mt={2}>
                  <FeatureRow
                    label={t('features.activeAlerts')}
                    value={formatLimit(plan.maxActiveAlerts)}
                  />
                  <FeatureRow
                    label={t('features.minFrequency')}
                    value={formatFrequency(plan.minFrequencyMinutes)}
                  />
                  <FeatureRow
                    label={t('features.priceHistory')}
                    value={formatDays(plan.priceHistoryDays)}
                  />
                  <FeatureRow
                    label={t('features.sources')}
                    value={formatLimit(plan.maxSources)}
                  />
                  <FeatureRow
                    label={t('features.push')}
                    value={plan.hasPushNotifications}
                  />
                  <FeatureRow
                    label={t('features.whatsapp')}
                    value={plan.hasWhatsappNotifications}
                  />
                  <FeatureRow
                    label={t('features.api')}
                    value={plan.hasApiAccess}
                  />
                </Stack>
              </CardContent>

              <CardActions sx={{ p: 2, pt: 0 }}>
                {isCurrent ? (
                  <Stack width="100%" spacing={1}>
                    <Button variant="outlined" disabled fullWidth>
                      {t('actions.current')}
                    </Button>
                    {plan.name !== 'free' && (
                      <Button
                        variant="text"
                        color="error"
                        size="small"
                        fullWidth
                        disabled={actionLoading === 'cancel'}
                        onClick={handleCancel}
                      >
                        {actionLoading === 'cancel' ? (
                          <CircularProgress size={20} />
                        ) : (
                          t('actions.cancel')
                        )}
                      </Button>
                    )}
                  </Stack>
                ) : (
                  <Button
                    variant={isPopular ? 'contained' : 'outlined'}
                    fullWidth
                    disabled={actionLoading !== null}
                    onClick={() => handleSubscribe(plan.id)}
                  >
                    {actionLoading === plan.id ? (
                      <CircularProgress size={20} />
                    ) : plan.priceCents === 0 ? (
                      t('actions.useFree')
                    ) : (
                      t('actions.subscribe')
                    )}
                  </Button>
                )}
              </CardActions>
            </Card>
          )
        })}
      </Stack>
    </Box>
  )
}
