/**
 * Type-safe translation keys: every t('...') call is checked against the
 * pt-BR files (the source language). A typo or a removed key is a compile
 * error. Other languages are checked for completeness by
 * tests/unit/i18n/locales.test.ts.
 */

import 'i18next'
import type admin from './locales/pt-BR/admin.json'
import type auth from './locales/pt-BR/auth.json'
import type common from './locales/pt-BR/common.json'
import type products from './locales/pt-BR/products.json'

declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common'
    resources: {
      admin: typeof admin
      auth: typeof auth
      common: typeof common
      products: typeof products
    }
  }
}
