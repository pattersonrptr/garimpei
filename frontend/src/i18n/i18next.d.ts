/**
 * Type-safe translation keys: every t('...') call is checked against the
 * pt-BR files (the source language). A typo or a removed key is a compile
 * error. Other languages are checked for completeness by
 * tests/unit/i18n/locales.test.ts.
 */

import 'i18next'
import type admin from './locales/pt-BR/admin.json'
import type alerts from './locales/pt-BR/alerts.json'
import type auth from './locales/pt-BR/auth.json'
import type common from './locales/pt-BR/common.json'
import type dashboard from './locales/pt-BR/dashboard.json'
import type plans from './locales/pt-BR/plans.json'
import type products from './locales/pt-BR/products.json'

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common'
    resources: {
      admin: typeof admin
      alerts: typeof alerts
      auth: typeof auth
      common: typeof common
      dashboard: typeof dashboard
      plans: typeof plans
      products: typeof products
    }
  }
}
