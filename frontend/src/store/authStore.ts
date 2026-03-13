import { create } from 'zustand'

interface Team {
  id: number
  team_code: string
  name: string
  domain: string
  cash: number
  revenue: number
  market_share: number
}

interface AuthState {
  token: string | null
  team: Team | null
  isAuthenticated: boolean
  setAuth: (token: string, team: Team) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('industrix_token'),
  team: JSON.parse(localStorage.getItem('industrix_team') || 'null'),
  isAuthenticated: !!localStorage.getItem('industrix_token'),

  setAuth: (token, team) => {
    localStorage.setItem('industrix_token', token)
    localStorage.setItem('industrix_team', JSON.stringify(team))
    set({ token, team, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('industrix_token')
    localStorage.removeItem('industrix_team')
    set({ token: null, team: null, isAuthenticated: false })
  }
}))