/**
 * Generic modal wrapper used by all resource forms.
 */

import CloseIcon from '@mui/icons-material/Close'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import IconButton from '@mui/material/IconButton'
import { useTranslation } from 'react-i18next'

interface GenericFormModalProps {
  open: boolean
  title: string
  onClose: () => void
  onSave: () => void
  saving?: boolean
  saveLabel?: string
  children: React.ReactNode
}

export function GenericFormModal({
  open,
  title,
  onClose,
  onSave,
  saving = false,
  saveLabel,
  children,
}: GenericFormModalProps) {
  const { t } = useTranslation()
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {title}
        <IconButton onClick={onClose} size="small" aria-label={t('actions.close')}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>{children}</DialogContent>

      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          {t('actions.cancel')}
        </Button>
        <Button
          onClick={onSave}
          variant="contained"
          disabled={saving}
        >
          {saving ? t('actions.saving') : (saveLabel ?? t('actions.save'))}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
