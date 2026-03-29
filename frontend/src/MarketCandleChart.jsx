import { useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  createChart,
} from 'lightweight-charts'

function hashString(s) {
  let h = 0
  for (let i = 0; i < s.length; i += 1) {
    h = Math.imul(31, h) + s.charCodeAt(i)
    h |= 0
  }
  return Math.abs(h)
}

/** Deterministic PRNG for repeatable series per symbol/site */
function mulberry32(a) {
  return () => {
    let t = (a += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function round2(n) {
  return Math.round(n * 100) / 100
}

function buildOHLCV(seedKey, barCount = 90) {
  const seed = hashString(seedKey)
  const rnd = mulberry32(seed)
  const candles = []
  const volumes = []
  let close = 95 + (seed % 85)
  const start = new Date(Date.UTC(2024, 0, 2))
  const volBase = 70_000 + (seed % 40_000)

  for (let i = 0; i < barCount; i += 1) {
    const d = new Date(start)
    d.setUTCDate(d.getUTCDate() + i)
    const time = d.toISOString().slice(0, 10)
    const open = close
    const bias = (seed % 17) * 0.01
    const change = (rnd() - 0.5 + bias) * 5.5
    close = Math.max(6, open + change)
    const high = Math.max(open, close) + rnd() * 3.2
    const low = Math.min(open, close) - rnd() * 3.2
    const up = close >= open
    candles.push({
      time,
      open: round2(open),
      high: round2(high),
      low: round2(low),
      close: round2(close),
    })
    volumes.push({
      time,
      value: Math.round(volBase + rnd() * 95_000 + i * 420),
      color: up ? 'rgba(9, 183, 128, 0.45)' : 'rgba(226, 80, 89, 0.45)',
    })
  }

  return { candles, volumes }
}

/**
 * In-app candlesticks + volume (canvas, no iframe). Series is deterministic from symbol + siteId.
 */
export function MarketCandleChart({ symbol, siteId }) {
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const seedKey = `${siteId}|${symbol}`
    const { candles, volumes } = buildOHLCV(seedKey)

    const w = Math.max(container.clientWidth, 280)
    const h = Math.max(container.clientHeight, 240)

    const chart = createChart(container, {
      width: w,
      height: h,
      layout: {
        background: { type: ColorType.Solid, color: '#000000' },
        textColor: '#8b95a8',
      },
      grid: {
        vertLines: { color: 'rgba(90, 140, 200, 0.15)' },
        horzLines: { color: 'rgba(90, 140, 200, 0.15)' },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { color: 'rgba(197, 201, 219, 0.35)', width: 1, style: 2 },
        horzLine: { color: 'rgba(197, 201, 219, 0.35)', width: 1, style: 2 },
      },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#09b780',
      downColor: '#e25059',
      borderUpColor: '#09b780',
      borderDownColor: '#e25059',
      wickUpColor: '#09b780',
      wickDownColor: '#e25059',
    })

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      base: 0,
    })
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.78, bottom: 0 },
    })

    candleSeries.setData(candles)
    volumeSeries.setData(volumes)
    chart.timeScale().fitContent()

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      const { width, height } = entry.contentRect
      const nw = Math.max(Math.floor(width), 200)
      const nh = Math.max(Math.floor(height), 200)
      chart.applyOptions({ width: nw, height: nh })
      chart.timeScale().fitContent()
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [symbol, siteId])

  return (
    <div
      ref={containerRef}
      className="map-popout-chart-host"
      role="img"
      aria-label={`Candlestick chart for ${symbol}`}
    />
  )
}
