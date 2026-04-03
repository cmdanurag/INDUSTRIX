import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
// import { MaterialMap } from '../MaterialMap'
import { productRows } from '../data/inventoryData.js'
import { TeamCard } from '../components/TeamCard'
import { Home } from './Home'
import { Inventory } from './Inventory'
import '../App.css'
import ProcurementPanel from '../components/procurement/ProcurementPanel'
import { useGameStore } from '../store/useGameStore'

function clampPopoutPosition(left, top) {
  const m = 12
  const vw = typeof window !== 'undefined' ? window.innerWidth : 1200
  const vh = typeof window !== 'undefined' ? window.innerHeight : 800
  const pw = Math.min(960, vw - m * 2)
  const ph = Math.min(720, vh - m * 2)
  return {
    left: Math.min(Math.max(m, left), vw - pw - m),
    top: Math.min(Math.max(m, top), vh - ph - m),
  }
}

const watchlist = [
  { symbol: 'AIRFRAME KIT', delta: '120', up: true },
  { symbol: 'WATER PUMP', delta: '84', up: true },
  { symbol: 'NOZZLE ASM', delta: '95', up: true },
  { symbol: 'FLIGHT CTRL', delta: '70', up: true },
]

const bottomQuotes = [
  { symbol: 'FRAME', value: '120', up: true },
  { symbol: 'HYDRAULICS', value: '84', up: true },
  { symbol: 'AVIONICS', value: '70', up: true },
  { symbol: 'PROPULSION', value: '180', up: true },
  { symbol: 'POWER', value: '140', up: false },
]

const leftModules = [
  { title: 'RAW MATERIALS', value: 'READY', active: true },
  { title: 'MARKETING', value: 'PIPELINE', active: false },
  { title: 'AUTOMATION LEVEL', value: '78%', active: false },
]

const alphaTeamCrew = {
  name: 'Alpha Team',
  members: [
    { name: 'John Reeves', role: 'Lead operator' },
    { name: 'Sara Chen', role: 'Supply analyst' },
    { name: 'Mike Ortiz', role: 'Field tech' },
  ],
}

const rawMaterialOptions = [
  { key: 'AIRFRAME_KIT', label: 'Airframe Kit', qty: '120' },
  { key: 'WATER_PUMP', label: 'Water Pump', qty: '84' },
  { key: 'NOZZLE_ASSEMBLY', label: 'Nozzle Assembly', qty: '95' },
  { key: 'FLIGHT_CONTROLLER', label: 'Flight Controller', qty: '70' },
]

function DashboardPage() {
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const team = useAuthStore((s) => s.team)

  const [selectedRawMaterial, setSelectedRawMaterial] = useState(rawMaterialOptions[0].key)
  const [mainTab, setMainTab] = useState('home')
  const [uiToast, setUiToast] = useState('')

  const toastTimerRef = useRef(null)

  const showToast = useCallback((message) => {
    setUiToast(message)
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    toastTimerRef.current = window.setTimeout(() => setUiToast(''), 2600)
  }, [])

  useEffect(
    () => () => {
      if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    },
    [],
  )

  const selectedMaterial = useMemo(
    () => rawMaterialOptions.find((m) => m.key === selectedRawMaterial) ?? rawMaterialOptions[0],
    [selectedRawMaterial],
  )

  return (
    <>
      <main className="terminal-shell">
        <section className="trading-screen">
          <aside className="left-panel">
            {leftModules.map((item) => (
              <article
                className={`left-quote-card module-card ${item.active ? 'active-module' : ''}`}
                key={item.title}
              >
                <div className="left-quote-head">
                  <div>
                    <div className="account-label">MODULE</div>
                    <div className="module-title">{item.title}</div>
                  </div>
                  <div className="quote-value-wrap">
                    {item.title === 'RAW MATERIALS' ? (
                      <select
                        className="raw-material-select"
                        value={selectedRawMaterial}
                        onChange={(e) => setSelectedRawMaterial(e.target.value)}
                      >
                        {rawMaterialOptions.map((m) => (
                          <option key={m.key} value={m.key}>
                            {m.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="module-value">{item.value}</div>
                    )}
                  </div>
                </div>
              </article>
            ))}

            <div className="left-market-bar">
              <span className="loss-label down">LOSS</span>
              <strong>199.99</strong>
            </div>

            {mainTab === 'home' ? (
              <div className="left-table-wrap left-crew-wrap">
                <div className="left-table-title">FIELD CREW</div>
                <TeamCard name={alphaTeamCrew.name} members={alphaTeamCrew.members} />
              </div>
            ) : (
              <div className="left-table-wrap">
                <div className="left-table-title">PRODUCTS</div>
                {productRows.map((row) => (
                  <div key={row.name}>{row.name}</div>
                ))}
              </div>
            )}

            <div className="left-footer-bar">
              {watchlist.map((item) => (
                <div key={item.symbol}>
                  {item.symbol} {item.delta}
                </div>
              ))}
            </div>
          </aside>

          <section className="main-panel">
            <header className="top-strip">
              <div className="top-title">
                {mainTab === 'home'
                  ? 'Home'
                  : mainTab === 'inventory'
                  ? 'Inventory'
                  : selectedMaterial.label}
              </div>

              <nav className="top-tabs">
                <button onClick={() => setMainTab('home')}>Home</button>
                <button onClick={() => setMainTab('market')}>Market</button>
                <button onClick={() => setMainTab('inventory')}>Inventory</button>
                <Link to="/event">Event</Link>
                <button
                  onClick={() => {
                    logout()
                    navigate('/login', { replace: true })
                  }}
                >
                  Logout
                </button>
              </nav>
            </header>

            {mainTab === 'market' ? (
              <section className="center-area">
                <div className="w-full h-full flex justify-center items-start">
                  <div className='w-full max-w-[1200px]'>
                <ProcurementPanel />
                </div>
                </div>
              </section>
            ) : (
              <section className="center-area">
                {mainTab === 'home' ? (
                  <Home />
                ) : (
                  <Inventory rows={productRows} showToast={showToast} />
                )}
              </section>
            )}

            <footer className="bottom-strip">
              STATUS READY
            </footer>
          </section>
        </section>
      </main>

      {uiToast && <div className="ui-toast">{uiToast}</div>}
    </>
  )
}

export default DashboardPage