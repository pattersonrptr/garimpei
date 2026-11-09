/**
 * Shown for any address the app does not know (instead of silently
 * redirecting, which made a mistyped link look like a broken app).
 */

import SearchOffIcon from '@mui/icons-material/SearchOff'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import { useTranslation } from 'react-i18next'
import { Link as RouterLink } from 'react-router-dom'
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher'
import { useAuth } from '@/context/AuthContext'

export function NotFoundPage() {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth()
  return (
    <Box
      component="main"
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        px: 2,
        bgcolor: 'background.default',
      }}
    >
      <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
        <LanguageSwitcher />
      </Box>
      <SearchOffIcon sx={{ fontSize: 64, color: 'text.disabled', mb: 2 }} />
      <Typography variant="h4" component="h1" fontWeight={700} gutterBottom>
        {t('notFound.title')}
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3, maxWidth: 420 }}>
        {t('notFound.body')}
      </Typography>
      <Button
        variant="contained"
        component={RouterLink}
        to={isAuthenticated ? '/dashboard' : '/'}
      >
        {isAuthenticated ? t('notFound.dashboard') : t('notFound.home')}
      </Button>
    </Box>
  )
}
