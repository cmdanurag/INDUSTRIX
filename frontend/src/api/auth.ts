import api from './client'

export const loginTeam = async (teamCode: string, password: string) => {
  const res = await api.post('/auth/login', { team_code: teamCode, password })
  return res.data
}

export const getMe = async () => {
  const res = await api.get('/auth/me')
  return res.data
}