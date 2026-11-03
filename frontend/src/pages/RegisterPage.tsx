/**
 * Public registration page.
 * Accessible without authentication — linked from the Login page.
 */

import Visibility from '@mui/icons-material/Visibility'
import VisibilityOff from '@mui/icons-material/VisibilityOff'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import IconButton from '@mui/material/IconButton'
import InputAdornment from '@mui/material/InputAdornment'
import Link from '@mui/material/Link'
import Paper from '@mui/material/Paper'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { useState } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher'
import { register } from '@/services/userService'
import { logger } from '@/lib/logger'

export function RegisterPage() {
  const navigate = useNavigate()
  const { t } = useTranslation('auth')
  const { enqueueSnackbar } = useSnackbar()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!username || !email || !password || !confirmPassword) {
      enqueueSnackbar(t('register.missingFields'), { variant: 'warning' })
      return
    }

    if (password !== confirmPassword) {
      enqueueSnackbar(t('register.passwordMismatch'), { variant: 'warning' })
      return
    }

    if (password.length < 8) {
      enqueueSnackbar(t('register.passwordTooShort'), { variant: 'warning' })
      return
    }

    setLoading(true)
    try {
      await register({ username, email, password })
      enqueueSnackbar(t('register.success'), { variant: 'success' })
      navigate('/login')
    } catch (err: unknown) {
      logger.error('Registration failed', { username }, err)

      // Extract JSON:API error detail if available
      const axiosErr = err as { response?: { data?: { errors?: { detail?: string }[] } } }
      const detail = axiosErr?.response?.data?.errors?.[0]?.detail
      enqueueSnackbar(detail ?? t('register.failed'), {
        variant: 'error',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
        position: 'relative',
      }}
    >
      <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
        <LanguageSwitcher color="primary" />
      </Box>
      <Paper sx={{ p: 4, width: '100%', maxWidth: 440 }}>
        <Typography variant="h5" fontWeight={700} gutterBottom textAlign="center">
          🏴‍☠️ Garimpei
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          textAlign="center"
          mb={3}
        >
          {t('register.subtitle')}
        </Typography>

        <Box component="form" onSubmit={handleSubmit} noValidate>
          <TextField
            label={t('fields.username')}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            fullWidth
            margin="normal"
            autoFocus
            autoComplete="username"
            disabled={loading}
          />

          <TextField
            label={t('fields.email')}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            fullWidth
            margin="normal"
            autoComplete="email"
            disabled={loading}
          />

          <TextField
            label={t('fields.password')}
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            fullWidth
            margin="normal"
            autoComplete="new-password"
            disabled={loading}
            helperText={t('register.passwordHelp')}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    onClick={() => setShowPassword((v) => !v)}
                    edge="end"
                    aria-label={t('fields.togglePassword')}
                  >
                    {showPassword ? <VisibilityOff /> : <Visibility />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          <TextField
            label={t('fields.confirmPassword')}
            type={showPassword ? 'text' : 'password'}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            fullWidth
            margin="normal"
            autoComplete="new-password"
            disabled={loading}
            error={confirmPassword.length > 0 && password !== confirmPassword}
            helperText={
              confirmPassword.length > 0 && password !== confirmPassword
                ? t('register.passwordMismatchShort')
                : undefined
            }
          />

          <Button
            type="submit"
            variant="contained"
            fullWidth
            sx={{ mt: 2 }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={22} color="inherit" /> : t('register.submit')}
          </Button>

          <Typography variant="body2" textAlign="center" color="text.secondary" mt={2}>
            {t('register.hasAccount')}{' '}
            <Link component={RouterLink} to="/login">
              {t('register.signIn')}
            </Link>
          </Typography>
        </Box>
      </Paper>
    </Box>
  )
}
