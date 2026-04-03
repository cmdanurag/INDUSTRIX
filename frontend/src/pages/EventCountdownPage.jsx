import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import './pages.css'

// Event start time (UTC).
const EVENT_START_MS = Date.UTC(2026, 5, 15, 14, 0, 0)

const EVENT_TITLE = 'Industrix live operations briefing'

const INSTRUCTIONS = [
  {
    title: 'Before you join',
    body: 'Use a current version of Chrome, Edge, or Firefox. Close heavy background tabs so screen share and video stay smooth.',
  },
  {
    title: 'Audio and video',
    body: 'Test your microphone and camera five minutes early. Use headphones to reduce echo for other participants.',
  },
  {
    title: 'Agenda overview',
    body: 'We will cover Q2 supply status, the firefighter drone program milestones, and open Q&A. Slides will be shared in the chat.',
  },
  {
    title: 'Materials to have ready',
    body: 'Have last week’s inventory export available if your site is asked to speak. Note any blockers in the shared doc linked in the invite.',
  },
  {
    title: 'Access and security',
    body: 'Join only from the link in your calendar invite. Do not forward the meeting link. Use your company SSO if prompted.',
  },
  {
    title: 'During the session',
    body: 'Stay muted unless called on. Use the raise-hand feature for questions. Chat is for links and short clarifications only.',
  },
  {
    title: 'Recording',
    body: 'This session may be recorded for teammates in other time zones. By staying in the call you agree to be part of the recording.',
  },
  {
    title: 'After the call',
    body: 'Action items will be posted within one business day. Reply in the thread attached to the recap email.',
  },
]

function pad(n) {
  return String(n).padStart(2, '0')
}

function getRemaining(targetMs) {
  const now = Date.now()
  const diff = Math.max(0, targetMs - now)
  const totalSec = Math.floor(diff / 1000)
  const days = Math.floor(totalSec / 86400)
  const hours = Math.floor((totalSec % 86400) / 3600)
  const minutes = Math.floor((totalSec % 3600) / 60)
  const seconds = totalSec % 60
  return { diff, days, hours, minutes, seconds, started: diff === 0 }
}

export default function EventCountdownPage() {
  const [tick, setTick] = useState(0)
  const [actionMsg, setActionMsg] = useState('')
  const instructionsRef = useRef(null)
  const msgTimerRef = useRef(null)

  const showActionMsg = (msg) => {
    setActionMsg(msg)
    if (msgTimerRef.current) window.clearTimeout(msgTimerRef.current)
    msgTimerRef.current = window.setTimeout(() => setActionMsg(''), 3200)
  }

  useEffect(
    () => () => {
      if (msgTimerRef.current) window.clearTimeout(msgTimerRef.current)
    },
    [],
  )

  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000)
    return () => window.clearInterval(id)
  }, [])

  const { days, hours, minutes, seconds, started } = useMemo(
    () => getRemaining(EVENT_START_MS),
    [tick],
  )

  const startDate = useMemo(() => {
    const d = new Date(EVENT_START_MS)
    return d.toLocaleString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short',
    })
  }, [])

  const copyEventDetails = async () => {
    const text = `${EVENT_TITLE}\nStarts: ${startDate}\n\n${window.location.origin}/event`
    try {
      await navigator.clipboard.writeText(text)
      showActionMsg('Event details copied to clipboard.')
    } catch {
      showActionMsg('Clipboard unavailable — copy the title and time manually.')
    }
  }

  const scrollToInstructions = () => {
    instructionsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    showActionMsg('Scrolled to instructions.')
  }

  const focusInstructionsPanel = () => {
    const el = document.querySelector('.event-instructions-scroll')
    el?.focus()
    showActionMsg('Instructions panel focused — use arrow keys to scroll.')
  }

  return (
    <div className="page-shell page-shell--event">
      <header className="page-header">
        <Link to="/" className="page-back">
          ← Dashboard
        </Link>
        <h1 className="page-title">{EVENT_TITLE}</h1>
        <p className="page-sub">Starts {startDate}</p>
      </header>

      <div className="event-actions" role="toolbar" aria-label="Event actions">
        <button type="button" className="event-action-btn" onClick={copyEventDetails}>
          Copy event details
        </button>
        <button type="button" className="event-action-btn" onClick={scrollToInstructions}>
          Jump to instructions
        </button>
        <button type="button" className="event-action-btn" onClick={focusInstructionsPanel}>
          Focus instructions
        </button>
      </div>
      {actionMsg ? (
        <p className="event-action-msg" role="status" aria-live="polite">
          {actionMsg}
        </p>
      ) : null}

      <section className="event-countdown" aria-live="polite">
        {started ? (
          <p className="event-live-banner">The event is live — join using your calendar link.</p>
        ) : (
          <>
            <h2 className="event-countdown-label">Starts in</h2>
            <div className="event-countdown-grid">
              <div className="event-countdown-unit">
                <span className="event-countdown-value">{days}</span>
                <span className="event-countdown-name">days</span>
              </div>
              <div className="event-countdown-unit">
                <span className="event-countdown-value">{pad(hours)}</span>
                <span className="event-countdown-name">hours</span>
              </div>
              <div className="event-countdown-unit">
                <span className="event-countdown-value">{pad(minutes)}</span>
                <span className="event-countdown-name">minutes</span>
              </div>
              <div className="event-countdown-unit">
                <span className="event-countdown-value">{pad(seconds)}</span>
                <span className="event-countdown-name">seconds</span>
              </div>
            </div>
          </>
        )}
      </section>

      <section className="event-instructions-section" ref={instructionsRef}>
        <h2 className="event-instructions-heading">Instructions</h2>
        <div className="event-instructions-scroll" tabIndex={0}>
          {INSTRUCTIONS.map((item) => (
            <article key={item.title} className="event-instruction-card">
              <h3>{item.title}</h3>
              <p>{item.body}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
