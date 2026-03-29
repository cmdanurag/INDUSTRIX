import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import * as topojson from 'topojson-client'
import worldData from 'world-atlas/countries-110m.json'

/**
 * World map with D3 + zoom/pan. Pins live in the zoom layer so they move with the map.
 */
export function MaterialMap({ sites, selectedSiteId, onSelectSite, zoomResetKey }) {
  const containerRef = useRef(null)
  const onSelectRef = useRef(onSelectSite)
  onSelectRef.current = onSelectSite

  const zoomTransformRef = useRef(d3.zoomIdentity)
  const lastZoomResetKeyRef = useRef(zoomResetKey)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const draw = () => {
      const width = container.clientWidth
      const height = container.clientHeight
      if (width < 32 || height < 32) return

      /* Fresh SVG each draw so zoom/click handlers are not stacked on resize */
      d3.select(container).selectAll('*').remove()

      if (lastZoomResetKeyRef.current !== zoomResetKey) {
        zoomTransformRef.current = d3.zoomIdentity
        lastZoomResetKeyRef.current = zoomResetKey
      }

      const countries = topojson.feature(worldData, worldData.objects.countries).features
      const projection = d3
        .geoMercator()
        .fitExtent(
          [
            [2, 2],
            [width - 2, height - 2],
          ],
          { type: 'FeatureCollection', features: countries },
        )
      const path = d3.geoPath(projection)

      const svg = d3
        .select(container)
        .selectAll('svg')
        .data([null])
        .join('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'material-map-svg')
        .attr('role', 'img')
        .attr('aria-label', 'Raw material sourcing map')

      const zoomLayer = svg
        .selectAll('g.map-zoom-layer')
        .data([null])
        .join('g')
        .attr('class', 'map-zoom-layer')

      zoomLayer
        .selectAll('path.map-land')
        .data(countries)
        .join('path')
        .attr('class', 'map-land')
        .attr('d', path)

      /* Pop-out is portaled; only nudge anchor near the pin */
      const panelReserve = { w: 64, h: 64 }

      const siteGroups = zoomLayer
        .selectAll('g.map-site')
        .data(sites, (d) => d.id)
        .join('g')
        .attr('class', 'map-site')
        .attr('transform', (d) => {
          const [x, y] = projection([d.lon, d.lat])
          return `translate(${x},${y})`
        })
        .style('cursor', 'pointer')

      siteGroups
        .selectAll('circle.map-site-glow')
        .data((d) => [d])
        .join('circle')
        .attr('class', 'map-site-glow')
        .attr('r', (d) => (d.id === selectedSiteId ? 18 : 14))
        .attr('fill', 'rgba(66, 165, 255, 0.12)')

      siteGroups
        .selectAll('circle.map-site-dot')
        .data((d) => [d])
        .join('circle')
        .attr('class', 'map-site-dot')
        .attr('r', (d) => (d.id === selectedSiteId ? 8 : 6))
        .attr('fill', (d) => (d.id === selectedSiteId ? '#5ddbff' : '#42a5ff'))
        .attr('stroke', 'rgba(255,255,255,0.35)')
        .attr('stroke-width', 1)

      siteGroups
        .on('mousedown', (event) => {
          event.stopPropagation()
        })
        .on('click', (event, d) => {
          event.stopPropagation()
          const [px, py] = d3.pointer(event, container)
          const maxX = Math.max(8, width - panelReserve.w)
          const maxY = Math.max(8, height - panelReserve.h)
          const x = Math.min(Math.max(8, px + 6), maxX)
          const y = Math.min(Math.max(8, py + 6), maxY)
          onSelectRef.current?.(d, { x, y })
        })

      const zoom = d3
        .zoom()
        .scaleExtent([0.35, 14])
        .on('zoom', (event) => {
          zoomTransformRef.current = event.transform
          zoomLayer.attr('transform', event.transform)
        })

      svg.on('click', (event) => {
        if (event.target.closest?.('.map-site')) return
        onSelectRef.current?.(null, null)
      })

      svg.call(zoom)
      zoomLayer.attr('transform', zoomTransformRef.current)
      svg.call(zoom.transform, zoomTransformRef.current)
    }

    draw()

    const ro = new ResizeObserver(() => {
      draw()
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      d3.select(container).selectAll('*').remove()
    }
  }, [sites, selectedSiteId, zoomResetKey])

  return <div className="material-map" ref={containerRef} />
}
