import '@testing-library/jest-dom'
import i18n from '@/i18n'

// Unit tests assert on the English UI texts; tests that need another
// language (e.g. pt-BR number formats) switch explicitly.
void i18n.changeLanguage('en')
