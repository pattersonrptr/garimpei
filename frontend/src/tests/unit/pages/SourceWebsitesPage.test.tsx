/**
 * Tests for pages/SourceWebsitesPage.tsx: what the admin is told when the API
 * refuses to delete a website (store) that still has offers (#253).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SnackbarProvider } from 'notistack'
import i18n from '@/i18n'
import { SourceWebsitesPage } from '@/pages/SourceWebsitesPage'
import { deleteSourceWebsite, getSourceWebsites } from '@/services/sourceWebsiteService'
import type { SourceWebsite } from '@/types/sourceWebsite'

vi.mock('@/services/sourceWebsiteService', () => ({
  getSourceWebsites: vi.fn(),
  deleteSourceWebsite: vi.fn(),
  createSourceWebsite: vi.fn(),
  updateSourceWebsite: vi.fn(),
}))

function site(id: string, name: string): SourceWebsite {
  return { id, name, baseUrl: `https://${name}.example.com`, isActive: true }
}

const SITES = [site('1', 'enjoei'), site('2', 'olx'), site('3', 'sebo')]

/** An axios-style error carrying one JSON:API error. */
function apiError(status: number, code: string, detail: string) {
  return {
    response: {
      status,
      data: { errors: [{ status: String(status), code, detail }] },
    },
  }
}

const SERVER_DETAIL = 'Server text that must not reach the admin'

function renderPage() {
  return render(
    <SnackbarProvider>
      <SourceWebsitesPage />
    </SnackbarProvider>,
  )
}

async function deleteOne(name: string, button = 'Delete') {
  const row = (await screen.findByText(name)).closest('[role="row"]') as HTMLElement
  await userEvent.click(within(row).getByRole('button', { name: button }))
  const dialog = await screen.findByRole('dialog')
  await userEvent.click(within(dialog).getByRole('button', { name: button }))
}

beforeEach(() => {
  vi.mocked(getSourceWebsites).mockResolvedValue({ items: SITES, total: SITES.length })
})

afterEach(async () => {
  vi.clearAllMocks()
  await i18n.changeLanguage('en')
})

describe('SourceWebsitesPage — single delete refused', () => {
  it('explains that the website still has offers and suggests deactivating, from the error code', async () => {
    vi.mocked(deleteSourceWebsite).mockRejectedValue(
      apiError(409, 'STORE_HAS_OFFERS', SERVER_DETAIL),
    )
    renderPage()

    await deleteOne('enjoei')

    expect(
      await screen.findByText(
        'Cannot delete: this website still has offers. Deactivate the website instead.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText(SERVER_DETAIL)).not.toBeInTheDocument()
    expect(screen.queryByText('Failed to delete source website')).not.toBeInTheDocument()
  })

  it('explains it in Portuguese when the admin uses pt-BR', async () => {
    await i18n.changeLanguage('pt-BR')
    vi.mocked(deleteSourceWebsite).mockRejectedValue(
      apiError(409, 'STORE_HAS_OFFERS', SERVER_DETAIL),
    )
    renderPage()

    await deleteOne('enjoei', 'Excluir')

    expect(
      await screen.findByText(
        'Não é possível excluir: este site ainda tem ofertas. Desative o site.',
      ),
    ).toBeInTheDocument()
  })

  it('keeps the generic message for any other failure', async () => {
    vi.mocked(deleteSourceWebsite).mockRejectedValue(
      apiError(500, 'INTERNAL_ERROR', SERVER_DETAIL),
    )
    renderPage()

    await deleteOne('enjoei')

    expect(await screen.findByText('Failed to delete source website')).toBeInTheDocument()
  })
})

describe('SourceWebsitesPage — bulk delete with mixed results', () => {
  it('tells how many websites were deleted and how many were kept, then refreshes the list', async () => {
    vi.mocked(deleteSourceWebsite).mockImplementation(async (id: string) => {
      if (id === '1') return undefined
      if (id === '2') throw apiError(409, 'STORE_HAS_OFFERS', SERVER_DETAIL)
      throw apiError(404, 'NOT_FOUND', SERVER_DETAIL)
    })
    renderPage()
    await screen.findByText('enjoei')

    await userEvent.click(screen.getByRole('checkbox', { name: /select all rows/i }))
    await userEvent.click(screen.getByRole('button', { name: /delete selected/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('Deleted: 1. Not deleted: 2.')).toBeInTheDocument()
    expect(deleteSourceWebsite).toHaveBeenCalledTimes(3)
    await waitFor(() => expect(getSourceWebsites).toHaveBeenCalledTimes(2))
  })
})
