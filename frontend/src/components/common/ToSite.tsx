import Box from '@mui/material/Box'
import CircularProgress from '@mui/material/CircularProgress'
import { useEffect } from 'react'
import { siteUrl } from '@/lib/site'

/** Leaves the back office for a page of the public site (Phase 5e). */
export function ToSite({ path }: { path: string }) {
  const target = siteUrl(path)
  useEffect(() => {
    window.location.replace(target)
  }, [target])
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
      <CircularProgress aria-label={target} />
    </Box>
  )
}
