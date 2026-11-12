/**
 * Product detail page: the listing, which of my alerts found it (and how much
 * I save), and its price history chart.
 */

import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import Divider from '@mui/material/Divider'
import Link from '@mui/material/Link'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemText from '@mui/material/ListItemText'
import Paper from '@mui/material/Paper'
import Typography from '@mui/material/Typography'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuth } from '@/context/AuthContext'
import { useProductDetails } from '@/hooks/useProductDetails'
import { matchesForProduct } from '@/lib/alertMatch'
import { formatCurrency } from '@/lib/formatters'
import { getPriceAlertsByUser } from '@/services/priceAlertService'
import type { PriceAlert } from '@/types/priceAlert'

/** Descriptions longer than this start collapsed. */
const DESCRIPTION_PREVIEW_CHARS = 600

export function ProductDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation(['products', 'common'])
  const { product, chartData, loading, error } = useProductDetails(id ?? '')
  const { userId } = useAuth()
  const [alerts, setAlerts] = useState<PriceAlert[]>([])
  const [showFullDescription, setShowFullDescription] = useState(false)

  useEffect(() => {
    if (userId) getPriceAlertsByUser(userId).then(setAlerts).catch(() => {})
  }, [userId])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error || !product) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(-1)}
          sx={{ mb: 2 }}
        >
          {t('common:actions.back')}
        </Button>
        <Alert severity="error">{error ?? t('detail.notFound')}</Alert>
      </Box>
    )
  }

  const matches = matchesForProduct(alerts, product)
  const description = product.description ?? ''
  const longDescription = description.length > DESCRIPTION_PREVIEW_CHARS
  const shownDescription =
    longDescription && !showFullDescription
      ? `${description.slice(0, DESCRIPTION_PREVIEW_CHARS).trimEnd()}…`
      : description

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate(-1)}
        sx={{ mb: 2 }}
      >
        {t('detail.back')}
      </Button>

      {/* ── Which of my alerts found it ── */}
      <Paper component="section" aria-labelledby="your-alerts-heading" sx={{ p: 3, mb: 3 }}>
        <Typography id="your-alerts-heading" variant="h6" fontWeight={600} gutterBottom>
          {t('detail.yourAlerts')}
        </Typography>
        {matches.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {t('detail.noMatchingAlert')}
          </Typography>
        ) : (
          <List dense disablePadding>
            {matches.map(({ alert, savings, isOpportunity }) => (
              <ListItem key={alert.id} disableGutters>
                <ListItemText
                  primary={
                    <>
                      <strong>{alert.searchTerm}</strong>
                      {' — '}
                      {t('detail.alertMax', { price: formatCurrency(alert.maxPrice) })}
                    </>
                  }
                  secondary={
                    savings == null
                      ? t('detail.noPriceYet')
                      : isOpportunity
                        ? t('detail.savings', { amount: formatCurrency(savings) })
                        : t('detail.aboveMax', { amount: formatCurrency(-savings) })
                  }
                />
                {isOpportunity && (
                  <Chip label={t('opportunity')} color="success" size="small" sx={{ ml: 1 }} />
                )}
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      {/* ── Product info ── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" fontWeight={600} gutterBottom>
          {product.title}
        </Typography>

        <Divider sx={{ my: 2 }} />

        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('fields.currentPrice')}
            </Typography>
            <Typography variant="h6" color="primary.main">
              {product.currentPrice != null
                ? formatCurrency(product.currentPrice)
                : '—'}
            </Typography>
          </Box>

          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('fields.condition')}
            </Typography>
            <Typography>{t(`condition.${product.condition}`)}</Typography>
          </Box>

          <Box>
            <Typography variant="body2" color="text.secondary">
              {t('detail.availability')}
            </Typography>
            <Chip
              label={product.isAvailable ? t('detail.available') : t('detail.unavailable')}
              color={product.isAvailable ? 'success' : 'default'}
              size="small"
            />
          </Box>

          {product.sellerName && (
            <Box>
              <Typography variant="body2" color="text.secondary">
                {t('fields.seller')}
              </Typography>
              <Typography>{product.sellerName}</Typography>
            </Box>
          )}

          {product.url && (
            <Box sx={{ gridColumn: '1 / -1' }}>
              <Typography variant="body2" color="text.secondary">
                {t('detail.sourceUrl')}
              </Typography>
              <Link
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{
                  display: 'block',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {product.url}
              </Link>
            </Box>
          )}
        </Box>

        {product.description && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {t('fields.description')}
            </Typography>
            <Typography sx={{ whiteSpace: 'pre-line' }}>{shownDescription}</Typography>
            {longDescription && (
              <Button size="small" onClick={() => setShowFullDescription((v) => !v)} sx={{ mt: 1 }}>
                {showFullDescription ? t('detail.showLess') : t('detail.showMore')}
              </Button>
            )}
          </>
        )}

        {product.imageUrls && (
          <Box sx={{ mt: 2 }}>
            <img
              src={product.imageUrls.split(',')[0]}
              alt={product.title}
              style={{ maxWidth: 300, height: 'auto', borderRadius: 8 }}
            />
          </Box>
        )}
      </Paper>

      {/* ── Price history chart ── */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" fontWeight={600} gutterBottom>
          {t('detail.priceHistory')}
        </Typography>

        {chartData.length > 0 ? (
          <Box sx={{ width: '100%', height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="dateLabel" />
                <YAxis
                  tickFormatter={(v: number) => formatCurrency(v)}
                  domain={['dataMin', 'dataMax']}
                  width={100}
                />
                <Tooltip
                  formatter={(v) => [typeof v === 'number' ? formatCurrency(v) : '—', t('detail.price')]}
                  labelFormatter={(_, payload) =>
                    payload?.[0]?.payload?.dateTime ?? ''
                  }
                />
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#1976d2"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {t('detail.noHistory')}
          </Typography>
        )}
      </Paper>
    </Box>
  )
}
