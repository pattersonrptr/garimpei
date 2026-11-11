/**
 * "Warn me" (Phase 4d): create an alert on a book.
 *
 * The public book page (Next.js) links here with the book, the condition and
 * a suggested price: /alertas/novo?isbn=…&condicao=usado&preco=25.90.
 * The route needs a login; RequireAuth sends visitors to log in or sign up
 * and back here with the same address.
 */

import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import InputAdornment from '@mui/material/InputAdornment'
import Link from '@mui/material/Link'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { useSnackbar } from 'notistack'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom'
import { PageHeader } from '@/components/common/PageHeader'
import { useAuth } from '@/context/AuthContext'
import { firstApiError, planLimitMessage } from '@/lib/apiErrors'
import { conditionFromLink, parsePrice, priceFromLink } from '@/lib/bookAlertLink'
import { formatCurrency } from '@/lib/formatters'
import { logger } from '@/lib/logger'
import { type Book, getBook } from '@/services/bookService'
import { createPriceAlert } from '@/services/priceAlertService'
import type { BookCondition } from '@/types/priceAlert'

type Problem = 'duplicate' | 'notFound' | null

export function NewBookAlertPage() {
  const { t } = useTranslation('alerts')
  const { t: tc } = useTranslation('common')
  const { userId } = useAuth()
  const { enqueueSnackbar } = useSnackbar()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const isbn = params.get('isbn') ?? ''

  const [book, setBook] = useState<Book | null>(null)
  const [loading, setLoading] = useState(true)
  const [condition, setCondition] = useState<BookCondition>(
    conditionFromLink(params.get('condicao')),
  )
  const [price, setPrice] = useState(priceFromLink(params.get('preco')))
  const [saving, setSaving] = useState(false)
  const [problem, setProblem] = useState<Problem>(null)

  useEffect(() => {
    let cancelled = false
    if (!isbn) {
      setLoading(false)
      return
    }
    getBook(isbn)
      .then((found) => !cancelled && setBook(found))
      .catch((err) => logger.warn('Book not found for alert', { isbn }, err))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [isbn])

  const maxPrice = parsePrice(price)
  const priceValid = !Number.isNaN(maxPrice)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!book || !priceValid || userId == null) return
    setSaving(true)
    setProblem(null)
    try {
      await createPriceAlert({ isbn: book.isbn13, condition, maxPrice, userId })
      enqueueSnackbar(t('book.created'), { variant: 'success' })
      navigate('/alerts')
    } catch (err) {
      const { status } = firstApiError(err)
      if (status === 409) setProblem('duplicate')
      else if (status === 404) setProblem('notFound')
      else
        enqueueSnackbar(planLimitMessage(err, tc) ?? t('toast.createFailed'), {
          variant: 'error',
        })
      logger.error('Book alert creation failed', { isbn }, err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (!book) {
    return (
      <Box>
        <PageHeader title={t('book.title')} />
        <Alert severity="warning">{t('book.notFound')}</Alert>
      </Box>
    )
  }

  const lowest =
    condition === 'new'
      ? book.lowestNew
      : condition === 'used'
        ? book.lowestUsed
        : minOf(book.lowestNew, book.lowestUsed)

  return (
    <Box>
      <PageHeader title={t('book.title')} subtitle={t('book.subtitle')} />
      <Paper sx={{ p: 3, maxWidth: 560 }}>
        <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
          {book.coverUrl && (
            <Box
              component="img"
              src={book.coverUrl}
              alt=""
              sx={{ width: 64, height: 'auto', borderRadius: 1, flexShrink: 0 }}
            />
          )}
          <Box>
            <Typography variant="h6" fontWeight={700}>
              {book.title}
            </Typography>
            {book.authors.length > 0 && (
              <Typography variant="body2" color="text.secondary">
                {book.authors.join(', ')}
              </Typography>
            )}
            {lowest != null && (
              <Typography variant="body2" sx={{ mt: 0.5 }}>
                {t('book.lowestNow', { price: formatCurrency(lowest) })}
              </Typography>
            )}
          </Box>
        </Stack>

        <Box component="form" onSubmit={handleSubmit} noValidate>
          <Stack spacing={2}>
            <TextField
              select
              label={t('book.condition')}
              value={condition}
              onChange={(e) => setCondition(e.target.value as BookCondition)}
            >
              <MenuItem value="used">{t('book.conditions.used')}</MenuItem>
              <MenuItem value="new">{t('book.conditions.new')}</MenuItem>
              <MenuItem value="any">{t('book.conditions.any')}</MenuItem>
            </TextField>
            <TextField
              label={t('fields.maxPrice')}
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              inputMode="decimal"
              error={price !== '' && !priceValid}
              helperText={t('book.priceHelp')}
              slotProps={{
                input: {
                  startAdornment: <InputAdornment position="start">R$</InputAdornment>,
                },
              }}
            />
            {problem === 'duplicate' && (
              <Alert severity="info">
                {t('book.duplicate')}{' '}
                <Link component={RouterLink} to="/alerts">
                  {t('book.seeAlerts')}
                </Link>
              </Alert>
            )}
            {problem === 'notFound' && <Alert severity="warning">{t('book.notFound')}</Alert>}
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={!priceValid || saving}
              startIcon={saving ? <CircularProgress size={18} color="inherit" /> : undefined}
            >
              {t('book.submit')}
            </Button>
          </Stack>
        </Box>
      </Paper>
    </Box>
  )
}

function minOf(a: number | null, b: number | null): number | null {
  if (a == null) return b
  if (b == null) return a
  return Math.min(a, b)
}
