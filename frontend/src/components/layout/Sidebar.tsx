/**
 * Collapsible navigation sidebar.
 *
 * User section:   Dashboard, My Alerts, Products
 * Admin section:  Users, Search Configs, Source Websites
 */

import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
import DashboardIcon from '@mui/icons-material/Dashboard'
import InventoryIcon from '@mui/icons-material/Inventory'
import ManageSearchIcon from '@mui/icons-material/ManageSearch'
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive'
import PeopleIcon from '@mui/icons-material/People'
import PublicIcon from '@mui/icons-material/Public'
import WorkspacePremiumIcon from '@mui/icons-material/WorkspacePremium'
import Divider from '@mui/material/Divider'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import ListSubheader from '@mui/material/ListSubheader'
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

const USER_ITEMS = [
  { label: 'nav.dashboard', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'nav.alerts', path: '/alerts', icon: <NotificationsActiveIcon /> },
  { label: 'nav.products', path: '/products', icon: <InventoryIcon /> },
  { label: 'nav.plans', path: '/plans', icon: <WorkspacePremiumIcon /> },
] as const

const ADMIN_ITEMS = [
  { label: 'nav.adminDashboard', path: '/admin', icon: <AdminPanelSettingsIcon /> },
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
    labelKey: (typeof USER_ITEMS | typeof ADMIN_ITEMS)[number]['label'],
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
      <List>
        {USER_ITEMS.map(({ label, path, icon }) => renderItem(label, path, icon))}
      </List>

      {isAdmin && (
        <>
          <Divider />
          <List
            subheader={
              open ? (
                <ListSubheader component="div" sx={{ lineHeight: '36px' }}>
                  {t('nav.admin')}
                </ListSubheader>
              ) : undefined
            }
          >
            {ADMIN_ITEMS.map(({ label, path, icon }) =>
              renderItem(label, path, icon),
            )}
          </List>
        </>
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
