import api from './client'

export const loginTeam = async (teamId: number, pin: string) => {
  const res = await api.post('/auth/login', { team_id: teamId, pin })
  return res.data
}

export const getMe = async () => {
  const res = await api.get('/auth/me')
  return res.data
}