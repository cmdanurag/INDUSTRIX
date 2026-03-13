import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { loginTeam } from '../api/auth'
import { useAuthStore } from '../store/authStore'

const CornerBracket = ({ position }: { position: 'tl' | 'tr' | 'bl' | 'br' }) => {
  const styles = {
    tl: 'top-0 left-0 border-t-2 border-l-2',
    tr: 'top-0 right-0 border-t-2 border-r-2',
    bl: 'bottom-0 left-0 border-b-2 border-l-2',
    br: 'bottom-0 right-0 border-b-2 border-r-2',
  }
  return <div className={`absolute w-4 h-4 border-brand-purple/70 ${styles[position]}`} />
}

export default function LoginPage() {
  const [teamCode, setTeamCode] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [focused, setFocused]   = useState<string | null>(null)

  const setAuth  = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!teamCode.trim() || !password.trim()) {
      setError('Both fields are required.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const data = await loginTeam(teamCode.trim().toUpperCase(), password)
      setAuth(data.access_token, data.team)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid team code or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="fixed top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-1/4 right-1/4 w-80 h-80 bg-pink-600/8 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, duration: 0.5 }}
          >
            <div className="flex items-center justify-center gap-3 mb-4">
              <div className="w-8 h-px bg-gradient-to-r from-transparent to-brand-purple" />
              <div className="w-2 h-2 rotate-45 bg-brand-purple shadow-glow" />
              <div className="w-8 h-px bg-gradient-to-l from-transparent to-brand-purple" />
            </div>
            <h1 className="font-display text-5xl font-bold tracking-widest text-white text-glow-purple animate-flicker">
              INDUSTRIX
            </h1>
            <p className="font-mono text-xs tracking-[0.3em] text-brand-purple/60 mt-2 uppercase">
              Market Simulation System v1.0
            </p>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.5 }}
          className="relative bg-brand-card border border-brand-border/60 rounded-sm p-8"
        >
          <CornerBracket position="tl" />
          <CornerBracket position="tr" />
          <CornerBracket position="bl" />
          <CornerBracket position="br" />

          <div className="mb-7">
            <p className="font-mono text-[10px] tracking-[0.25em] text-brand-purple/50 uppercase mb-1">
              // Authentication Required
            </p>
            <h2 className="font-display text-xl font-semibold tracking-wider text-white/90">
              Team Login
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block font-mono text-[10px] tracking-[0.2em] text-brand-purple/60 uppercase mb-2">
                Team Code
              </label>
              <div className={`relative transition-all duration-300 ${focused === 'code' ? 'drop-shadow-[0_0_8px_rgba(168,85,247,0.3)]' : ''}`}>
                <input
                  type="text"
                  value={teamCode}
                  onChange={(e) => setTeamCode(e.target.value.toUpperCase())}
                  onFocus={() => setFocused('code')}
                  onBlur={() => setFocused(null)}
                  placeholder="e.g. ALPHA-01"
                  maxLength={10}
                  className="input-cyber uppercase tracking-widest"
                  autoComplete="off"
                  spellCheck={false}
                />
                {focused === 'code' && (
                  <motion.div
                    className="absolute bottom-0 left-0 right-0 h-px bg-brand-purple"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.2 }}
                  />
                )}
              </div>
            </div>

            <div>
              <label className="block font-mono text-[10px] tracking-[0.2em] text-brand-purple/60 uppercase mb-2">
                Password
              </label>
              <div className={`relative transition-all duration-300 ${focused === 'pass' ? 'drop-shadow-[0_0_8px_rgba(168,85,247,0.3)]' : ''}`}>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocused('pass')}
                  onBlur={() => setFocused(null)}
                  placeholder="••••••••"
                  className="input-cyber"
                />
                {focused === 'pass' && (
                  <motion.div
                    className="absolute bottom-0 left-0 right-0 h-px bg-brand-purple"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.2 }}
                  />
                )}
              </div>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-start gap-2 bg-red-500/10 border border-red-500/30 rounded-sm px-3 py-2"
                >
                  <span className="text-red-400 font-mono text-[10px] tracking-wider mt-0.5">ERR</span>
                  <p className="text-red-300/80 text-xs font-mono leading-relaxed">{error}</p>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="pt-1">
              <button type="submit" disabled={loading} className="btn-cyber disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? (
                  <span className="flex items-center justify-center gap-3">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span className="font-mono text-sm tracking-widest">AUTHENTICATING...</span>
                  </span>
                ) : (
                  <span className="font-mono tracking-[0.3em]">ENTER SYSTEM</span>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 pt-5 border-t border-brand-border/40 flex justify-between items-center">
            <p className="font-mono text-[9px] tracking-widest text-white/20 uppercase">
              DOPE · Dept. of Production Engg.
            </p>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse-slow" />
              <span className="font-mono text-[9px] text-green-400/60 tracking-wider">SYSTEM ONLINE</span>
            </div>
          </div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="text-center font-mono text-[9px] tracking-widest text-white/15 uppercase mt-6"
        >
          Team codes will be distributed on event day
        </motion.p>
      </motion.div>
    </div>
  )
}