# Internationalization (i18n)

The UI ships in **Português (Brasil)** (default) and **English**. It is built
with [i18next](https://www.i18next.com/) + [react-i18next](https://react.i18next.com/).

## Layout

```
src/i18n/
├── index.ts          # i18next setup: language detection, fallback, <html lang>
├── resources.ts      # finds every locales/<lang>/<namespace>.json automatically
├── mui.ts            # MUI + DataGrid built-in texts per language
├── i18next.d.ts      # type-safe keys (checked against pt-BR)
└── locales/
    ├── pt-BR/        # source language: complete by definition, used as fallback
    │   ├── common.json     # layout, navigation, shared buttons and labels
    │   ├── auth.json       # login and register
    │   ├── landing.json    # public home page
    │   ├── dashboard.json
    │   ├── alerts.json
    │   ├── products.json
    │   ├── plans.json
    │   └── admin.json      # admin dashboard, users, search configs, sites
    └── en/           # same files, same keys
```

## Adding a language (e.g. Spanish)

1. Copy the source folder: `cp -r src/i18n/locales/pt-BR src/i18n/locales/es`
2. Translate the values in every JSON file. Keep the keys and the
   `{{variables}}` as they are. Set `languageName` in `common.json`
   (`"Español"`): that is the label shown in the language menu.
3. Plurals use the language's own forms: `key_one`, `key_other`, and also
   `key_few` / `key_many` where the language needs them
   ([plural rules](https://www.i18next.com/translation-function/plurals)).
4. Optional: add the MUI locales in `mui.ts` (`esES` from `@mui/material/locale`
   and `@mui/x-data-grid/locales`) so the grid's own texts are translated too.
   Without it, they fall back to English.
5. Run `npm run test`. `tests/unit/i18n/locales.test.ts` fails if a key or a
   variable is missing.

No other code changes: the new folder is discovered at build time, shows up
in the language menu, and is picked automatically for browsers set to it.

## Adding text to the UI

1. Add the key to `pt-BR` **and** every other language, in the right namespace.
2. Use it in the component:

   ```tsx
   const { t } = useTranslation('alerts')          // one namespace
   t('toast.created')
   t('toast.bulkDeleted', { count: ids.length })   // plural
   const { t } = useTranslation(['alerts', 'common'])
   t('common:actions.edit')                        // shared label
   ```

A key that does not exist in pt-BR is a TypeScript error (`npx tsc -b`).

## Behavior

- **Which language:** the one picked in the menu (saved in `localStorage` as
  `garimpei.language`), otherwise the browser's, otherwise pt-BR.
  `en-US`, `en-GB`… resolve to `en`.
- **Missing translation:** falls back to pt-BR.
- **Numbers and dates** follow the active language (`src/lib/formatters.ts`).
  Prices are always in Brazilian reais (BRL), because the marketplaces are
  Brazilian; only the formatting changes (`R$ 1.234,56` / `R$1,234.56`).
- **Not translated here:** product data from the marketplaces, API error
  messages (sent by the backend in English) and the alert emails (pt-BR).
