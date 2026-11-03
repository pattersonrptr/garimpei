/**
 * Language picker. Lists every language found in src/i18n/locales, so a new
 * language shows up here without code changes.
 */

import TranslateIcon from '@mui/icons-material/Translate'
import Button from '@mui/material/Button'
import ListItemText from '@mui/material/ListItemText'
import Menu from '@mui/material/Menu'
import MenuItem from '@mui/material/MenuItem'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { SUPPORTED_LANGUAGES } from '@/i18n'

interface LanguageSwitcherProps {
  color?: 'inherit' | 'primary'
}

export function LanguageSwitcher({ color = 'inherit' }: LanguageSwitcherProps) {
  const { t, i18n } = useTranslation()
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
  const active =
    SUPPORTED_LANGUAGES.find((l) => l.code === i18n.resolvedLanguage) ??
    SUPPORTED_LANGUAGES[0]

  return (
    <>
      <Button
        color={color}
        startIcon={<TranslateIcon />}
        onClick={(e) => setAnchor(e.currentTarget)}
        aria-label={t('language.change')}
        aria-haspopup="menu"
      >
        {active.name}
      </Button>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
        {SUPPORTED_LANGUAGES.map((language) => (
          <MenuItem
            key={language.code}
            selected={language.code === active.code}
            lang={language.code}
            onClick={() => {
              void i18n.changeLanguage(language.code)
              setAnchor(null)
            }}
          >
            <ListItemText primary={language.name} />
          </MenuItem>
        ))}
      </Menu>
    </>
  )
}
