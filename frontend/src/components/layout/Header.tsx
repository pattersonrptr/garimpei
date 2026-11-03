/**
 * Top navigation bar.
 */

import MenuIcon from '@mui/icons-material/Menu'
import AppBar from '@mui/material/AppBar'
import IconButton from '@mui/material/IconButton'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import { useState } from 'react'
import { useAuth } from '@/context/AuthContext'
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog'
import { useTranslation } from 'react-i18next'
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher'

interface HeaderProps {
  onMenuClick: () => void
  sidebarOpen: boolean
}

export function Header({ onMenuClick }: HeaderProps) {
  const { t } = useTranslation()
  const { logout } = useAuth()
  const [confirmOpen, setConfirmOpen] = useState(false)

  return (
    <>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={onMenuClick}
            sx={{ mr: 2 }}
            aria-label={t('layout.toggleSidebar')}
          >
            <MenuIcon />
          </IconButton>

          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 700 }}>
            🏴‍☠️ Garimpei
          </Typography>

          <LanguageSwitcher />
          <Button color="inherit" onClick={() => setConfirmOpen(true)}>
            {t('layout.logout')}
          </Button>
        </Toolbar>
      </AppBar>

      <ConfirmationDialog
        open={confirmOpen}
        title={t('layout.signOutTitle')}
        message={t('layout.signOutMessage')}
        confirmLabel={t('layout.signOutConfirm')}
        cancelLabel={t('layout.signOutCancel')}
        onConfirm={() => { setConfirmOpen(false); logout() }}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  )
}
