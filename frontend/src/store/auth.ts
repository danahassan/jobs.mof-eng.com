import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../lib/api'

export interface AuthUser {
  id: number
  full_name: string
  email: string
  role: string
  avatar_filename: string | null
}

interface AuthState {
  user: AuthUser | null
  setUser: (u: AuthUser | null) => void
  fetchMe: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (u) => set({ user: u }),
      fetchMe: async () => {
        try {
          const { data } = await api.get<AuthUser>('/auth/me')
          set({ user: data })
        } catch {
          set({ user: null })
        }
      },
      logout: async () => {
        await api.post('/auth/logout')
        set({ user: null })
      },
    }),
    { name: 'auth-store' },
  ),
)
