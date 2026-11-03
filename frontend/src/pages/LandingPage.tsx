/**
 * Public landing page — explains Garimpei and invites users to sign up.
 */

import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import SearchIcon from '@mui/icons-material/Search'
import TrendingDownIcon from '@mui/icons-material/TrendingDown'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Container from '@mui/material/Container'
import Grid from '@mui/material/Grid'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher'

const features = [
  { key: 'track', icon: <SearchIcon sx={{ fontSize: 40 }} color="primary" /> },
  {
    key: 'alerts',
    icon: <NotificationsActiveIcon sx={{ fontSize: 40 }} color="primary" />,
  },
  { key: 'deals', icon: <TrendingDownIcon sx={{ fontSize: 40 }} color="primary" /> },
] as const

export function LandingPage() {
  const navigate = useNavigate()
  const { t } = useTranslation('landing')

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Hero */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #1565c0 0%, #0d47a1 100%)',
          color: 'white',
          py: { xs: 8, md: 12 },
          px: 2,
          position: 'relative',
        }}
      >
        <Box sx={{ position: 'absolute', top: 16, right: 16 }}>
          <LanguageSwitcher />
        </Box>
        <Container maxWidth="md">
          <Typography
            variant="h2"
            fontWeight={800}
            gutterBottom
            sx={{ fontSize: { xs: '2rem', sm: '2.5rem', md: '3rem' } }}
          >
            🏴‍☠️ Garimpei
          </Typography>
          <Typography
            variant="h5"
            sx={{
              mb: 4,
              opacity: 0.9,
              fontSize: { xs: '1.1rem', md: '1.4rem' },
              maxWidth: 600,
            }}
          >
            {t('hero.tagline')}
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/register')}
              sx={{
                bgcolor: 'white',
                color: 'primary.dark',
                fontWeight: 700,
                px: 4,
                '&:hover': { bgcolor: 'grey.100' },
              }}
            >
              {t('hero.signUp')}
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/login')}
              sx={{
                borderColor: 'rgba(255,255,255,0.5)',
                color: 'white',
                fontWeight: 600,
                px: 4,
                '&:hover': {
                  borderColor: 'white',
                  bgcolor: 'rgba(255,255,255,0.1)',
                },
              }}
            >
              {t('hero.signIn')}
            </Button>
          </Stack>
        </Container>
      </Box>

      {/* Features */}
      <Container maxWidth="md" sx={{ py: { xs: 6, md: 10 } }}>
        <Typography
          variant="h4"
          fontWeight={700}
          textAlign="center"
          gutterBottom
          sx={{ fontSize: { xs: '1.5rem', md: '2rem' } }}
        >
          {t('howItWorks.title')}
        </Typography>
        <Typography
          variant="body1"
          color="text.secondary"
          textAlign="center"
          sx={{ mb: 6, maxWidth: 500, mx: 'auto' }}
        >
          {t('howItWorks.subtitle')}
        </Typography>

        <Grid container spacing={4}>
          {features.map((f) => (
            <Grid size={{ xs: 12, md: 4 }} key={f.key}>
              <Paper
                elevation={0}
                sx={{
                  p: 3,
                  textAlign: 'center',
                  height: '100%',
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 2,
                }}
              >
                <Box sx={{ mb: 2 }}>{f.icon}</Box>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  {t(`features.${f.key}.title`)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(`features.${f.key}.description`)}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* CTA */}
      <Box sx={{ bgcolor: 'grey.50', py: { xs: 6, md: 8 }, px: 2 }}>
        <Container maxWidth="sm" sx={{ textAlign: 'center' }}>
          <Typography
            variant="h5"
            fontWeight={700}
            gutterBottom
            sx={{ fontSize: { xs: '1.3rem', md: '1.5rem' } }}
          >
            {t('cta.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            {t('cta.subtitle')}
          </Typography>
          <Button
            variant="contained"
            size="large"
            onClick={() => navigate('/register')}
            sx={{ fontWeight: 700, px: 5 }}
          >
            {t('cta.button')}
          </Button>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ py: 3, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Garimpei © {new Date().getFullYear()} — {t('footer')}
        </Typography>
      </Box>
    </Box>
  )
}
