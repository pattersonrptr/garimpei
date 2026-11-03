/**
 * App root — sets up providers and the router.
 */

import CssBaseline from '@mui/material/CssBaseline'
import { createTheme, ThemeProvider } from '@mui/material/styles'
import { SnackbarProvider } from 'notistack'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { muiLocaleFor } from '@/i18n/mui'
import { AppRouter } from '@/router'

const themeOptions = {
  palette: {
    primary: { main: '#0d47a1' },
    secondary: { main: '#ff6f00' },
    background: { default: '#f5f5f5' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
  },
}

export default function App() {
  const { i18n } = useTranslation()
  const language = i18n.resolvedLanguage ?? i18n.language
  // MUI's own texts (pagination, DataGrid…) follow the active language
  const theme = useMemo(
    () => createTheme(themeOptions, ...muiLocaleFor(language)),
    [language],
  )

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <SnackbarProvider
        maxSnack={3}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        autoHideDuration={4000}
      >
        <BrowserRouter>
          <AuthProvider>
            <AppRouter />
          </AuthProvider>
        </BrowserRouter>
      </SnackbarProvider>
    </ThemeProvider>
  )
}

