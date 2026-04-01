import { useEffect, useMemo, useState } from 'react'
import { MaterialMap } from '../../MaterialMap'
import { useGameStore } from '../../store/useGameStore'

const COMPONENTS = [
  'airframe',
  'propulsion',
  'avionics',
  'fire_suppression',
  'sensing_safety',
  'battery',
]

export default function ProcurementPanel() {
  const {
    selectedComponent,
    setSelectedComponent,
    sources,
    selectedSource,
    selectSource,
    updateProcurement,
    totalCost,
    funds,
    fetchSources,
    submitProcurement,
    fetchCostEstimate,
  } = useGameStore()

  const [quantity, setQuantity] = useState(0)
  const [transport, setTransport] = useState<'air' | 'rail' | 'road'>('road')

  // Filter sources based on selected component (safe)
  const filteredSources = useMemo(() => {
    return (sources || []).filter((s) => s.component === selectedComponent)
  }, [sources, selectedComponent])

  // Load sources on mount
  useEffect(() => {
    fetchSources()
  }, [fetchSources])

  // When user clicks confirm
  const handleConfirm = async () => {
    if (!selectedSource) return

    updateProcurement(selectedComponent, {
      source_id: selectedSource.id,
      quantity,
      transport_mode: transport,
    })

    await submitProcurement(selectedComponent)
    await fetchCostEstimate()
  }

  // Map click handler
  const handleMapSelect = (site: any) => {
    if (!site) return
    selectSource(site)
  }

  console.log("sources",sources)

  return (
    <div className="flex flex-col gap-4 p-4">

      {/* 🔹 Component Selector */}
      <div className="flex gap-2 flex-wrap">
        {COMPONENTS.map((comp) => (
          <button
            key={comp}
            onClick={() => setSelectedComponent(comp)}
            className={`px-3 py-1 border rounded text-sm ${
              selectedComponent === comp
                ? 'bg-purple-600 text-white'
                : 'bg-black text-white/60 border-white/10'
            }`}
          >
            {comp}
          </button>
        ))}
      </div>

      {/* 🔹 Map + Controls */}
      <div className="grid grid-cols-[2fr_1fr] gap-4 h-[500px]">

        {/* 🌍 Map */}
        <div className="h-full min-h-[400px]">
          <MaterialMap
            sites={filteredSources}
            selectedSiteId={selectedSource?.id || null}
            onSelectSite={handleMapSelect}
            zoomResetKey={selectedComponent}
          />
        </div>

        {/* 📦 Right Panel */}
        <div className="flex flex-col gap-4 border border-white/10 p-4 rounded">

          {/* Supplier Info */}
          {selectedSource ? (
            <div>
              <h2 className="text-lg font-bold text-white">
                {selectedSource.name}
              </h2>
              <p className="text-sm text-white/50">
                {selectedSource.component}
              </p>

              <div className="mt-2 text-sm space-y-1">
                <div>Quality: {selectedSource.quality_mean}</div>
                <div>Consistency: {selectedSource.quality_sigma}</div>
                <div>Cost/unit: {selectedSource.base_cost_per_unit} CU</div>
              </div>
            </div>
          ) : (
            <div className="text-white/40 text-sm">
              Select a supplier from map
            </div>
          )}

          {/* Controls */}
          <div className="flex flex-col gap-2">
            <input
              type="number"
              placeholder="Quantity"
              className="input-cyber"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />

            <select
              className="input-cyber"
              value={transport}
              onChange={(e) =>
                setTransport(e.target.value as 'air' | 'rail' | 'road')
              }
            >
              <option value="road">Road (cheap, risky)</option>
              <option value="rail">Rail (balanced)</option>
              <option value="air">Air (expensive, safe)</option>
            </select>

            <button className="btn-cyber" onClick={handleConfirm}>
              Confirm Order
            </button>
          </div>

          {/* Cost Summary */}
          <div className="mt-4 border-t border-white/10 pt-3 text-sm">
            <div>Total Cost: {Math.round(totalCost)} CU</div>
            <div className="text-white/50">
              Funds Left: {Math.round(funds - totalCost)} CU
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}