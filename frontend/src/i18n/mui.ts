/**
 * MUI component translations (pagination, DataGrid toolbar, empty states…).
 *
 * Optional per language: a language without an entry here gets MUI's English
 * texts while the app itself is still translated.
 */

import { enUS as coreEnUS, ptBR as corePtBR } from '@mui/material/locale'
import { enUS as gridEnUS, ptBR as gridPtBR } from '@mui/x-data-grid/locales'

type MuiLocale = [typeof coreEnUS, typeof gridEnUS]

const MUI_LOCALES: Record<string, MuiLocale> = {
  'pt-BR': [corePtBR, gridPtBR],
  en: [coreEnUS, gridEnUS],
}

export function muiLocaleFor(language: string): MuiLocale {
  return MUI_LOCALES[language] ?? MUI_LOCALES.en
}
