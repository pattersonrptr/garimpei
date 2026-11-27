/**
 * Tests for pages/UsersPage.tsx: what the admin is told when the API
 * refuses to delete a user (#239).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SnackbarProvider } from 'notistack'
import i18n from '@/i18n'
import { UsersPage } from '@/pages/UsersPage'
import { deleteUser, getUsers } from '@/services/userService'
import type { User } from '@/types/user'

vi.mock('@/services/userService', () => ({
  getUsers: vi.fn(),
  deleteUser: vi.fn(),
  updateUser: vi.fn(),
}))

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ isSuperuser: true }),
}))

function user(id: string, username: string): User {
  return {
    id,
    username,
    email: `${username}@example.com`,
    isActive: true,
    isStaff: false,
    isSuperuser: false,
    createdAt: '2026-11-01T10:00:00',
  }
}

const USERS = [user('1', 'ana'), user('2', 'bia'), user('3', 'caio')]

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
      <UsersPage />
    </SnackbarProvider>,
  )
}

async function deleteOne(username: string) {
  const row = (await screen.findByText(username)).closest('[role="row"]') as HTMLElement
  await userEvent.click(within(row).getByRole('button', { name: 'Delete' }))
  const dialog = await screen.findByRole('dialog')
  await userEvent.click(within(dialog).getByRole('button', { name: /delete|excluir/i }))
}

beforeEach(() => {
  vi.mocked(getUsers).mockResolvedValue({ items: USERS, total: USERS.length })
})

afterEach(async () => {
  vi.clearAllMocks()
  await i18n.changeLanguage('en')
})

describe('UsersPage — single delete refused', () => {
  it('explains that the user has data and suggests deactivating, from the error code', async () => {
    vi.mocked(deleteUser).mockRejectedValue(apiError(409, 'USER_HAS_DATA', SERVER_DETAIL))
    renderPage()

    await deleteOne('ana')

    expect(
      await screen.findByText(
        'Cannot delete: this user still has data. Deactivate the user instead.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText(SERVER_DETAIL)).not.toBeInTheDocument()
    expect(screen.queryByText('Failed to delete user')).not.toBeInTheDocument()
  })

  it('explains it in Portuguese when the admin uses pt-BR', async () => {
    await i18n.changeLanguage('pt-BR')
    vi.mocked(deleteUser).mockRejectedValue(apiError(409, 'USER_HAS_DATA', SERVER_DETAIL))
    renderPage()

    const row = (await screen.findByText('ana')).closest('[role="row"]') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Excluir' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Excluir' }))

    expect(
      await screen.findByText(
        'Não é possível excluir: este usuário ainda tem dados. Desative o usuário.',
      ),
    ).toBeInTheDocument()
  })

  it('keeps the generic message for any other failure', async () => {
    vi.mocked(deleteUser).mockRejectedValue(apiError(500, 'INTERNAL_ERROR', SERVER_DETAIL))
    renderPage()

    await deleteOne('ana')

    expect(await screen.findByText('Failed to delete user')).toBeInTheDocument()
  })
})

describe('UsersPage — bulk delete with mixed results', () => {
  it('tells how many users were deleted and how many were kept, then refreshes the list', async () => {
    vi.mocked(deleteUser).mockImplementation(async (id: string) => {
      if (id === '1') return undefined
      if (id === '2') throw apiError(409, 'USER_HAS_DATA', SERVER_DETAIL)
      throw apiError(404, 'NOT_FOUND', SERVER_DETAIL)
    })
    renderPage()
    await screen.findByText('ana')

    await userEvent.click(screen.getByRole('checkbox', { name: /select all rows/i }))
    await userEvent.click(screen.getByRole('button', { name: /delete selected/i }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('Deleted: 1. Not deleted: 2.')).toBeInTheDocument()
    expect(deleteUser).toHaveBeenCalledTimes(3)
    await waitFor(() => expect(getUsers).toHaveBeenCalledTimes(2))
  })
})
