import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import { loginTeam } from '../api/auth'
import { useAuthStore } from '../store/authStore'

export default function LoginPage() {
  const [teamId, setTeamId]   = useState('')
  const [pin, setPin]         = useState('')
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)
  const [focused, setFocused] = useState<string | null>(null)

  const setAuth  = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!teamId.trim() || !pin.trim()) {
      setError('Both fields are required.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const data = await loginTeam(parseInt(teamId), pin.trim())
      setAuth(data.access_token, data.team)
      navigate('/dashboard')
    } catch (err: unknown) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined
      setError(typeof detail === 'string' ? detail : 'Invalid team ID or PIN.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{ background: '#000', minHeight: '100vh' }}
      className="flex items-center justify-center px-4"
    >
      {/* Subtle grid overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `
            linear-gradient(rgba(120,177,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(120,177,255,0.03) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
        }}
      />

      {/* Ambient glow */}
      <div
        className="fixed pointer-events-none"
        style={{
          top: '20%', left: '30%',
          width: '400px', height: '400px',
          background: 'radial-gradient(circle, rgba(120,177,255,0.06) 0%, transparent 70%)',
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="w-full relative"
        style={{ maxWidth: '400px', zIndex: 1 }}
      >
        {/* Header */}
        <div className="mb-8 text-center">
          {/* Top rule */}
          <div className="flex items-center gap-3 mb-6 justify-center">
            <div style={{ height: '1px', width: '60px', background: 'rgba(120,177,255,0.3)' }} />
            <div style={{
              width: '6px', height: '6px',
              background: 'rgba(120,177,255,0.8)',
              transform: 'rotate(45deg)',
              boxShadow: '0 0 8px rgba(120,177,255,0.6)',
            }} />
            <div style={{ height: '1px', width: '60px', background: 'rgba(120,177,255,0.3)' }} />
          </div>

          <motion.h1
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, duration: 0.4 }}
            style={{
              fontFamily: "'Segoe UI', monospace",
              fontSize: '2.8rem',
              fontWeight: 700,
              letterSpacing: '0.25em',
              color: '#fff',
              textShadow: '0 0 30px rgba(120,177,255,0.5), 0 0 60px rgba(120,177,255,0.2)',
              margin: 0,
              lineHeight: 1,
            }}
          >
            INDUSTRIX
          </motion.h1>

          <p style={{
            fontFamily: 'monospace',
            fontSize: '0.65rem',
            letterSpacing: '0.3em',
            color: 'rgba(120,177,255,0.5)',
            marginTop: '8px',
            textTransform: 'uppercase',
          }}>
            Fire-Fighting Drone Simulation · v1.0
          </p>
        </div>

        {/* Card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(120,177,255,0.15)',
            padding: '2rem',
            position: 'relative',
          }}
        >
          {/* Corner brackets */}
          {[
            { top: -1, left: -1, borderTop: '2px solid rgba(120,177,255,0.6)', borderLeft: '2px solid rgba(120,177,255,0.6)' },
            { top: -1, right: -1, borderTop: '2px solid rgba(120,177,255,0.6)', borderRight: '2px solid rgba(120,177,255,0.6)' },
            { bottom: -1, left: -1, borderBottom: '2px solid rgba(120,177,255,0.6)', borderLeft: '2px solid rgba(120,177,255,0.6)' },
            { bottom: -1, right: -1, borderBottom: '2px solid rgba(120,177,255,0.6)', borderRight: '2px solid rgba(120,177,255,0.6)' },
          ].map((s, i) => (
            <div key={i} style={{ position: 'absolute', width: 14, height: 14, ...s }} />
          ))}

          {/* Card header */}
          <div style={{ marginBottom: '1.5rem' }}>
            <p style={{
              fontFamily: 'monospace',
              fontSize: '0.6rem',
              letterSpacing: '0.25em',
              color: 'rgba(120,177,255,0.4)',
              textTransform: 'uppercase',
              marginBottom: '4px',
            }}>
              // Authentication Required
            </p>
            <p style={{
              fontFamily: "'Segoe UI', sans-serif",
              fontSize: '1.1rem',
              fontWeight: 600,
              color: 'rgba(255,255,255,0.9)',
              letterSpacing: '0.05em',
              margin: 0,
            }}>
              Team Login
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

            {/* Team ID */}
            <div>
              <label style={{
                display: 'block',
                fontFamily: 'monospace',
                fontSize: '0.6rem',
                letterSpacing: '0.2em',
                color: 'rgba(120,177,255,0.5)',
                textTransform: 'uppercase',
                marginBottom: '8px',
              }}>
                Team ID
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="number"
                  value={teamId}
                  onChange={(e) => setTeamId(e.target.value)}
                  onFocus={() => setFocused('id')}
                  onBlur={() => setFocused(null)}
                  placeholder="e.g. 1"
                  autoComplete="off"
                  style={{
                    width: '100%',
                    background: 'rgba(0,0,0,0.6)',
                    border: `1px solid ${focused === 'id' ? 'rgba(120,177,255,0.6)' : 'rgba(120,177,255,0.15)'}`,
                    padding: '10px 14px',
                    color: '#fff',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    letterSpacing: '0.1em',
                    outline: 'none',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.2s',
                    boxShadow: focused === 'id' ? '0 0 12px rgba(120,177,255,0.15)' : 'none',
                  }}
                />
                {focused === 'id' && (
                  <motion.div
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.2 }}
                    style={{
                      position: 'absolute', bottom: 0, left: 0, right: 0,
                      height: '1px', background: 'rgba(120,177,255,0.8)',
                      transformOrigin: 'left',
                    }}
                  />
                )}
              </div>
            </div>

            {/* PIN */}
            <div>
              <label style={{
                display: 'block',
                fontFamily: 'monospace',
                fontSize: '0.6rem',
                letterSpacing: '0.2em',
                color: 'rgba(120,177,255,0.5)',
                textTransform: 'uppercase',
                marginBottom: '8px',
              }}>
                PIN
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="password"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  onFocus={() => setFocused('pin')}
                  onBlur={() => setFocused(null)}
                  placeholder="••••••••"
                  style={{
                    width: '100%',
                    background: 'rgba(0,0,0,0.6)',
                    border: `1px solid ${focused === 'pin' ? 'rgba(120,177,255,0.6)' : 'rgba(120,177,255,0.15)'}`,
                    padding: '10px 14px',
                    color: '#fff',
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                    outline: 'none',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.2s',
                    boxShadow: focused === 'pin' ? '0 0 12px rgba(120,177,255,0.15)' : 'none',
                  }}
                />
                {focused === 'pin' && (
                  <motion.div
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.2 }}
                    style={{
                      position: 'absolute', bottom: 0, left: 0, right: 0,
                      height: '1px', background: 'rgba(120,177,255,0.8)',
                      transformOrigin: 'left',
                    }}
                  />
                )}
              </div>
            </div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  style={{
                    background: 'rgba(255,80,80,0.08)',
                    border: '1px solid rgba(255,80,80,0.25)',
                    padding: '8px 12px',
                    display: 'flex',
                    gap: '8px',
                    alignItems: 'flex-start',
                  }}
                >
                  <span style={{ fontFamily: 'monospace', fontSize: '0.6rem', color: 'rgba(255,100,100,0.8)', letterSpacing: '0.1em', marginTop: '2px' }}>ERR</span>
                  <p style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'rgba(255,150,150,0.8)', margin: 0 }}>{error}</p>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '12px',
                background: loading ? 'rgba(120,177,255,0.1)' : 'rgba(120,177,255,0.15)',
                border: '1px solid rgba(120,177,255,0.4)',
                color: loading ? 'rgba(120,177,255,0.5)' : 'rgba(120,177,255,0.9)',
                fontFamily: 'monospace',
                fontSize: '0.75rem',
                letterSpacing: '0.25em',
                textTransform: 'uppercase',
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
                marginTop: '4px',
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.background = 'rgba(120,177,255,0.25)'
                  e.currentTarget.style.boxShadow = '0 0 16px rgba(120,177,255,0.2)'
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(120,177,255,0.15)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              {loading ? (
                <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                  <span style={{
                    width: '12px', height: '12px',
                    border: '1.5px solid rgba(120,177,255,0.3)',
                    borderTopColor: 'rgba(120,177,255,0.8)',
                    borderRadius: '50%',
                    display: 'inline-block',
                    animation: 'spin 0.8s linear infinite',
                  }} />
                  Authenticating...
                </span>
              ) : (
                'Enter System →'
              )}
            </button>

          </form>

          {/* Footer */}
          <div style={{
            marginTop: '1.5rem',
            paddingTop: '1rem',
            borderTop: '1px solid rgba(120,177,255,0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ fontFamily: 'monospace', fontSize: '0.6rem', letterSpacing: '0.15em', color: 'rgba(255,255,255,0.15)', textTransform: 'uppercase' }}>
              DOPE · Production Engg.
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%',
                background: '#4ade80',
                boxShadow: '0 0 6px rgba(74,222,128,0.6)',
                animation: 'pulse 2s infinite',
              }} />
              <span style={{ fontFamily: 'monospace', fontSize: '0.6rem', color: 'rgba(74,222,128,0.6)', letterSpacing: '0.1em' }}>
                SYSTEM ONLINE
              </span>
            </span>
          </div>
        </motion.div>

        {/* Bottom hint */}
        <p style={{
          textAlign: 'center',
          fontFamily: 'monospace',
          fontSize: '0.6rem',
          letterSpacing: '0.2em',
          color: 'rgba(255,255,255,0.1)',
          textTransform: 'uppercase',
          marginTop: '1.5rem',
        }}>
          Team IDs will be distributed on event day
        </p>
      </motion.div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        input[type=number]::-webkit-inner-spin-button,
        input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; }
        input[type=number] { -moz-appearance: textfield; }
        input::placeholder { color: rgba(255,255,255,0.2); }
      `}</style>
    </div>
  )
}
