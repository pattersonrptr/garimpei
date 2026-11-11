/**
 * Collapsible navigation sidebar.
 *
 * User section:   Dashboard, My Alerts, Products
 * Admin section:  Users, Search Configs, Source Websites
 */

import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
import ManageSearchIcon from '@mui/icons-material/ManageSearch'
import InventoryIcon from '@mui/icons-material/Inventory'
import PeopleIcon from '@mui/icons-material/People'
import PublicIcon from '@mui/icons-material/Public'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Tooltip from '@mui/material/Tooltip'
import useMediaQuery from '@mui/material/useMediaQuery'
import { useTheme } from '@mui/material/styles'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useTranslation } from 'react-i18next'

export const SIDEBAR_WIDTH_EXPANDED = 220
export const SIDEBAR_WIDTH_COLLAPSED = 60

interface SidebarProps {
  open: boolean
  onClose?: () => void
}

/**
 * The back office is for administrators only (Phase 5e). Users manage their
 * alerts and account on the site; the old user pages are gone.
 */
const ADMIN_ITEMS = [
  { label: 'nav.adminDashboard', path: '/admin', icon: <AdminPanelSettingsIcon /> },
  { label: 'nav.products', path: '/products', icon: <InventoryIcon /> },
  { label: 'nav.users', path: '/admin/users', icon: <PeopleIcon /> },
  { label: 'nav.searchConfigs', path: '/admin/search-configs', icon: <ManageSearchIcon /> },
  { label: 'nav.sourceWebsites', path: '/admin/source-websites', icon: <PublicIcon /> },
] as const

export function Sidebar({ open, onClose }: SidebarProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { isStaff, isSuperuser } = useAuth()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const width = open ? SIDEBAR_WIDTH_EXPANDED : SIDEBAR_WIDTH_COLLAPSED
  const isAdmin = isStaff || isSuperuser

  function renderItem(
    labelKey: (typeof ADMIN_ITEMS)[number]['label'],
    path: string,
    icon: React.ReactNode,
  ) {
    const label = t(labelKey)
    const active =
      path === '/admin'
        ? location.pathname === path
        : location.pathname.startsWith(path)
    return (
      <Tooltip key={path} title={open ? '' : label} placement="right">
        <ListItemButton
          selected={active}
          onClick={() => {
            navigate(path)
            if (isMobile && onClose) onClose()
          }}
          sx={{ justifyContent: open ? 'initial' : 'center', px: 2 }}
        >
          <ListItemIcon
            sx={{
              minWidth: 0,
              mr: open ? 2 : 'auto',
              justifyContent: 'center',
              color: active ? 'primary.main' : 'inherit',
            }}
          >
            {icon}
          </ListItemIcon>
          {open && <ListItemText primary={label} />}
        </ListItemButton>
      </Tooltip>
    )
  }

  const content = (
    <>
      {isAdmin && (
        <List>
          {ADMIN_ITEMS.map(({ label, path, icon }) => renderItem(label, path, icon))}
        </List>
      )}
    </>
  )

  // On mobile: temporary drawer (overlay). On desktop: permanent drawer.
  if (isMobile) {
    return (
      <Drawer
        variant="temporary"
        open={open}
        onClose={onClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          '& .MuiDrawer-paper': {
            width: SIDEBAR_WIDTH_EXPANDED,
            boxSizing: 'border-box',
            mt: '64px',
          },
        }}
      >
        {content}
      </Drawer>
    )
  }

  return (
    <Drawer
      variant="permanent"
      sx={{
        width,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width,
          boxSizing: 'border-box',
          overflowX: 'hidden',
          transition: 'width 0.2s ease',
          mt: '64px',
        },
      }}
    >
      {content}
    </Drawer>
  )
}
