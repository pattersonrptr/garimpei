/**
 * Page header with title and optional action button.
 */

import AddIcon from '@mui/icons-material/Add'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actionLabel?: string
  onAction?: () => void
}

export function PageHeader({ title, subtitle, actionLabel, onAction }: PageHeaderProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        mb: 3,
      }}
    >
      <Box>
        <Typography variant="h5" component="h1" fontWeight={600}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary" mt={0.5}>
            {subtitle}
          </Typography>
        )}
      </Box>

      {actionLabel && onAction && (
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={onAction}
        >
          {actionLabel}
        </Button>
      )}
    </Box>
  )
}
