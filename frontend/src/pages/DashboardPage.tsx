import { useAuthStore } from '../store/authStore'
import { useNavigate } from 'react-router-dom'

export default function DashboardPage() {
  const { team, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="font-display text-4xl font-bold text-brand-purple text-glow-purple tracking-widest">
          WELCOME, {team?.name || 'TEAM'}
        </h1>
        <p className="font-mono text-sm text-white/40 tracking-wider">
          Dashboard coming next — authentication successful
        </p>
        <button
          onClick={handleLogout}
          className="font-mono text-xs tracking-widest text-red-400/60 hover:text-red-400 transition-colors uppercase border border-red-500/20 px-4 py-2 rounded-sm"
        >
          Logout
        </button>
      </div>
    </div>
  )
}