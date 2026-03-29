import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { MaterialMap } from '../MaterialMap'
import { MarketCandleChart } from '../MarketCandleChart'
import { productRows } from '../data/inventoryData.js'
import { TeamCard } from '../components/TeamCard'
import { Home } from './Home'
import { Inventory } from './Inventory'
import '../App.css'

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

// Firefighting drone status widgets (kept intentionally compact)
const watchlist = [
  { symbol: 'AIRFRAME KIT', delta: '120', up: true },
  { symbol: 'WATER PUMP', delta: '84', up: true },
  { symbol: 'NOZZLE ASM', delta: '95', up: true },
  { symbol: 'FLIGHT CTRL', delta: '70', up: true },
]

const tableRows = [
  ['RANGE 52 WEEK', '43.36'],
  ['BID', '61.12'],
  ['ASK', '29.87'],
  ['MKT CAP', '212.19'],
  ['DIV YIELD', '43.86'],
  ['P/E', '61.12'],
  ['OPEN', '29.87'],
  ['VOLUME', '212.19'],
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

/**
 * Sourcing sites (map pins). `tradingViewSymbol` labels the in-app candle chart and seeds demo OHLCV data.
 */
const MATERIAL_SITES = [
  {
    id: 'af-sea',
    materialKey: 'AIRFRAME_KIT',
    name: 'Pacific composites hub',
    region: 'Seattle, USA',
    lat: 47.6062,
    lon: -122.3321,
    tradingViewSymbol: 'NYSE:BA',
  },
  {
    id: 'af-tls',
    materialKey: 'AIRFRAME_KIT',
    name: 'EU airframe alloys',
    region: 'Toulouse, FR',
    lat: 43.6047,
    lon: 1.4442,
    tradingViewSymbol: 'EPA:AIR',
  },
  {
    id: 'wp-det',
    materialKey: 'WATER_PUMP',
    name: 'Pump casting cluster',
    region: 'Detroit, USA',
    lat: 42.3314,
    lon: -83.0458,
    tradingViewSymbol: 'NYSE:XYL',
  },
  {
    id: 'wp-stu',
    materialKey: 'WATER_PUMP',
    name: 'Hydraulics foundry belt',
    region: 'Stuttgart, DE',
    lat: 48.7758,
    lon: 9.1829,
    tradingViewSymbol: 'NYSE:CAT',
  },
  {
    id: 'nz-hou',
    materialKey: 'NOZZLE_ASSEMBLY',
    name: 'Precision nozzle line',
    region: 'Houston, USA',
    lat: 29.7604,
    lon: -95.3698,
    tradingViewSymbol: 'NYSE:ITT',
  },
  {
    id: 'nz-sgp',
    materialKey: 'NOZZLE_ASSEMBLY',
    name: 'Asia nozzle integrators',
    region: 'Singapore',
    lat: 1.3521,
    lon: 103.8198,
    tradingViewSymbol: 'NYSE:EMR',
  },
  {
    id: 'fc-sjo',
    materialKey: 'FLIGHT_CONTROLLER',
    name: 'Controller PCB corridor',
    region: 'San Jose, USA',
    lat: 37.3382,
    lon: -121.8863,
    tradingViewSymbol: 'NASDAQ:MU',
  },
  {
    id: 'fc-szn',
    materialKey: 'FLIGHT_CONTROLLER',
    name: 'Shenzhen EMS lane',
    region: 'Shenzhen, CN',
    lat: 22.5431,
    lon: 114.0579,
    tradingViewSymbol: 'NASDAQ:NVDA',
  },
]

const summaryRows = [
  ['RANGE', '120.34'],
  ['52 WEEK', '43.86'],
  ['OPEN', '61.12'],
  ['VOLUME', '22.97'],
  ['MKT CAP', '212.19'],
]

const specialEvents = [
  { text: 'Corruption probe expanded in procurement division.', up: false },
  { text: 'Logistics crisis delays delivery of batteries.', up: false },
  { text: 'Automation audit flags minor inconsistencies.', up: true },
  { text: 'New marketing campaign approved for drone pilots.', up: true },
  { text: 'Raw materials prices spike; contingency invoked.', up: false },
  { text: 'Telemetry software patch improves stability.', up: true },
  { text: 'Equipment shortage forces a short production pause.', up: false },
  { text: 'Supplier quality score upgraded for rotors.', up: true },
  { text: 'Crisis resolved after alternative shipping route secured.', up: true },
  { text: 'Risk review scheduled for avionics components.', up: false },
]

function DashboardPage() {
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const team = useAuthStore((s) => s.team)

  const [selectedRawMaterial, setSelectedRawMaterial] = useState(rawMaterialOptions[0].key)
  const [mapPopup, setMapPopup] = useState(null)
  const [popoutPos, setPopoutPos] = useState({ left: 24, top: 24 })
  const [mainTab, setMainTab] = useState('home')
  const [orderSide, setOrderSide] = useState(null)
  const [uiToast, setUiToast] = useState('')

  const mapWrapRef = useRef(null)
  const popoutPanelRef = useRef(null)
  const popoutPosRef = useRef(popoutPos)
  const popoutDragRef = useRef(null)
  const toastTimerRef = useRef(null)

  const showToast = useCallback((message) => {
    setUiToast(message)
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    toastTimerRef.current = window.setTimeout(() => setUiToast(''), 2600)
  }, [])

  useEffect(() => {
    popoutPosRef.current = popoutPos
  }, [popoutPos])

  useEffect(
    () => () => {
      if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current)
    },
    [],
  )

  useLayoutEffect(() => {
    if (!mapPopup || !mapWrapRef.current) return
    const r = mapWrapRef.current.getBoundingClientRect()
    const next = clampPopoutPosition(r.left + mapPopup.x, r.top + mapPopup.y)
    setPopoutPos(next)
    popoutPosRef.current = next
  }, [mapPopup])

  const selectedMaterial = useMemo(
    () => rawMaterialOptions.find((m) => m.key === selectedRawMaterial) ?? rawMaterialOptions[0],
    [selectedRawMaterial],
  )

  const visibleSites = useMemo(
    () => MATERIAL_SITES.filter((s) => s.materialKey === selectedRawMaterial),
    [selectedRawMaterial],
  )

  const handleMapSelect = useCallback((site, pos) => {
    if (!site || !pos) {
      setMapPopup(null)
      return
    }
    setMapPopup({ site, x: pos.x, y: pos.y })
  }, [])

  const onPopoutDragPointerDown = useCallback((e) => {
    if (e.target.closest('.map-floating-close')) return
    if (e.pointerType === 'mouse' && e.button !== 0) return
    popoutDragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      startL: popoutPosRef.current.left,
      startT: popoutPosRef.current.top,
    }
    e.currentTarget.setPointerCapture(e.pointerId)
  }, [])

  const onPopoutDragPointerMove = useCallback((e) => {
    const d = popoutDragRef.current
    if (!d || e.pointerId !== d.pointerId) return
    setPopoutPos(
      clampPopoutPosition(
        d.startL + (e.clientX - d.startX),
        d.startT + (e.clientY - d.startY),
      ),
    )
  }, [])

  const onPopoutDragPointerUp = useCallback((e) => {
    const d = popoutDragRef.current
    if (!d || e.pointerId !== d.pointerId) return
    popoutDragRef.current = null
    try {
      e.currentTarget.releasePointerCapture(e.pointerId)
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    setMapPopup((prev) => {
      if (!prev?.site) return prev
      if (prev.site.materialKey !== selectedRawMaterial) return null
      return prev
    })
  }, [selectedRawMaterial])

  const headlineValue = mapPopup ? mapPopup.site.tradingViewSymbol : selectedMaterial.qty
  const headlineSub = mapPopup
    ? `${mapPopup.site.name} · market chart`
    : 'On-hand qty · click a map pin for market chart'

  const chartPopout = mapPopup
    ? createPortal(
      <div
        ref={popoutPanelRef}
        className="map-floating-panel map-floating-panel--popout"
        style={{ left: popoutPos.left, top: popoutPos.top }}
        role="dialog"
        aria-modal="false"
        aria-label="Draggable market chart window"
      >
        <div
          className="map-floating-head map-floating-head--draggable"
          onPointerDown={onPopoutDragPointerDown}
          onPointerMove={onPopoutDragPointerMove}
          onPointerUp={onPopoutDragPointerUp}
          onPointerCancel={onPopoutDragPointerUp}
        >
          <div>
            <div className="map-floating-title">{mapPopup.site.name}</div>
            <div className="map-floating-region">
              {mapPopup.site.region}
              <span className="map-popout-drag-hint"> · drag to move</span>
            </div>
          </div>
          <button
            type="button"
            className="map-floating-close"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={() => setMapPopup(null)}
            aria-label="Close chart window"
          >
            ×
          </button>
        </div>
        <div className="map-popout-body">
          <div className="map-popout-meta">
            <div className="map-floating-label">Market proxy · candles + volume</div>
            <div className="map-chart-symbol">
              <code>{mapPopup.site.tradingViewSymbol}</code>
              <span className="map-chart-note">
                In-app chart (no iframe). Series is demo OHLCV seeded from this symbol — swap for live data when
                ready.
              </span>
            </div>
          </div>
          <MarketCandleChart
            key={mapPopup.site.id}
            siteId={mapPopup.site.id}
            symbol={mapPopup.site.tradingViewSymbol}
          />
        </div>
      </div>,
      document.body,
    )
    : null

  return (
    <>
      <main className="terminal-shell">
      <section className="trading-screen" aria-label="Stock trading dashboard mockup">
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
                      aria-label="Select raw material"
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
              <div className="left-crew-body">
                <TeamCard name={alphaTeamCrew.name} members={alphaTeamCrew.members} />
              </div>
            </div>
          ) : (
            <div className="left-table-wrap">
              <div className="left-table-title">PRODUCTS FOR FIRE FIGHTING DRONE</div>
              <div className="left-table-header">
                <span>PRODUCT</span>
                <span>STAGE</span>
                <span>QTY</span>
                <span>RISK</span>
              </div>
              <div className="left-table-body">
                {productRows.map((row) => (
                  <div className="left-table-row" key={row.name}>
                    <span className="symbol-cell">
                      <i className={row.up ? 'dot up-dot' : 'dot down-dot'} />
                      {row.name}
                    </span>
                    <span>{row.stage}</span>
                    <span>{row.qty}</span>
                    <span className={row.up ? 'up' : 'down'}>{row.risk}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="left-footer-bar">
            {watchlist.map((item) => (
              <div className="watch-row" key={item.symbol}>
                <span>{item.symbol}</span>
                <span className={item.up ? 'up' : 'down'}>{item.delta}</span>
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
              <button
                type="button"
                className={mainTab === 'home' ? 'active' : ''}
                onClick={() => {
                  setMainTab('home')
                  showToast('Home — crew roster in the left panel')
                }}
              >
                Home
              </button>
              <button
                type="button"
                className={mainTab === 'market' ? 'active' : ''}
                onClick={() => {
                  setMainTab('market')
                  showToast('Market tab — map & chart (demo)')
                }}
              >
                Market
              </button>
              <button
                type="button"
                className={mainTab === 'inventory' ? 'active' : ''}
                onClick={() => {
                  setMainTab('inventory')
                  showToast('Inventory — full SKU table')
                }}
              >
                Inventory
              </button>
              <Link to="/event" className="top-tabs-link">
                Event
              </Link>
              <button
                type="button"
                className="top-tabs-link"
                onClick={() => {
                  logout()
                  navigate('/login', { replace: true })
                }}
              >
                Logout
                {team?.team_code ? ` (${team.team_code})` : ''}
              </button>
            </nav>
          </header>

          {mainTab === 'market' ? (
            <section className="center-area">
              <div className="center-main">
                <div className="top-summary-grid">
                  <div className="price-box">
                    <div className="action-row">
                      <button
                        type="button"
                        className={orderSide === 'buy' ? 'action-row-buy-active' : ''}
                        onClick={() => {
                          setOrderSide('buy')
                          showToast('BUY intent recorded (demo — not a real order)')
                        }}
                      >
                        BUY
                      </button>
                      <button
                        type="button"
                        className={orderSide === 'sell' ? 'action-row-sell-active' : ''}
                        onClick={() => {
                          setOrderSide('sell')
                          showToast('SELL intent recorded (demo — not a real order)')
                        }}
                      >
                        SELL
                      </button>
                    </div>
                    <div className="big-price">
                      <span className="value">{headlineValue}</span>
                      <span className="map-headline-sub">{headlineSub}</span>
                    </div>
                  </div>

                  <div className="summary-box">
                    <div>
                      {summaryRows.map(([label, value]) => (
                        <div className="metric-row" key={`left-${label}`}>
                          <span>{label}</span>
                          <span>{value}</span>
                        </div>
                      ))}
                    </div>
                    <div>
                      {summaryRows.map(([label, value]) => (
                        <div className="metric-row" key={`right-${label}`}>
                          <span>{label}</span>
                          <span>{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="material-map-wrap" ref={mapWrapRef}>
                  <div className="map-interaction-hint" aria-hidden="true">
                    Scroll / pinch to zoom · drag to pan
                  </div>
                  <MaterialMap
                    sites={visibleSites}
                    selectedSiteId={mapPopup?.site?.id ?? null}
                    onSelectSite={handleMapSelect}
                    zoomResetKey={selectedRawMaterial}
                  />
                </div>
                <div className="map-hint">
                  Click a pin — chart opens in a draggable floating window. Drag the title bar to move it.
                </div>
              </div>

              <aside className="right-column">
                <div className="side-metrics">
                  {tableRows.map(([label, value]) => (
                    <div className="metric-row" key={`side-${label}`}>
                      <span>{label}</span>
                      <span>{value}</span>
                    </div>
                  ))}
                </div>

                <div className="news-panel">
                  <div className="news-title">SPECIAL EVENTS</div>
                  <div className="news-list">
                    {specialEvents.map((item, idx) => (
                      <p key={`${idx}-${item.text}`}>
                        <span className={item.up ? 'up' : 'down'}>{item.up ? '▲' : '▼'}</span>{' '}
                        {item.text}
                      </p>
                    ))}
                  </div>
                </div>
              </aside>
            </section>
          ) : (
            <section className="center-area center-area--tab-page">
              <div className="center-main center-main--tab-page">
                {mainTab === 'home' ? (
                  <Home />
                ) : (
                  <Inventory rows={productRows} showToast={showToast} />
                )}
              </div>
            </section>
          )}

          <footer className="bottom-strip">
            <div className="status-chip">AUTO 78%</div>
            <div className="bottom-quotes">
              {bottomQuotes.map((quote) => (
                <div key={`${quote.symbol}-bottom`} className="bottom-row">
                  <span>{quote.symbol}</span>
                  <span className={quote.up ? 'up' : 'down'}>{quote.value}</span>
                </div>
              ))}
            </div>
            <div className="status-text">FIREFIGHTER DRONE READY</div>
          </footer>
        </section>

        <div className="scanlines" aria-hidden="true">
          <div className="scanline-overlay" />
        </div>
      </section>
    </main>
    {chartPopout}
    {uiToast ? (
      <div className="ui-toast" role="status" aria-live="polite">
        {uiToast}
      </div>
    ) : null}
    </>
  )
}

export default DashboardPage
