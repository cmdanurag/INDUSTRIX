import { useEffect, useState } from 'react';
import { FiCheckCircle, FiCircle, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { useProcurementStore, useGameStore, useInventoryStore } from '../store';
import { useNotificationStore } from '../store/useNotificationStore';
import { ComponentTabs, SendDecisionsButton } from '../components/SharedComponents';

export const Procurement = () => {
  const {
    decisions,
    initialDecisions,
    sourcesByComponent,
    selectedComponent,
    setComponent,
    setDecision,
    isBuying,
    setIsBuying,
    transports,
    projectedCosts,
    fetchSources,
    fetchTransports,
    fetchExistingDecisions,
    submitDecisions
  } = useProcurementStore();

  const { phase } = useGameStore();
  const { funds, fetchInventory, components } = useInventoryStore();
  const { addToast } = useNotificationStore();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');
  const [lastSavedAt, setLastSavedAt] = useState('');
  const [showTransportDetails, setShowTransportDetails] = useState(false);

  // Initial data load
  useEffect(() => {
    fetchSources();
    fetchTransports();
    fetchInventory();
    fetchExistingDecisions();
  }, [fetchSources, fetchTransports, fetchInventory, fetchExistingDecisions]);

  const currentDecision = decisions[selectedComponent];
  const activeSources = sourcesByComponent[selectedComponent] || [];
  const selectedSource = activeSources.find(s => s.id === currentDecision.source_id) || activeSources[0];

  useEffect(() => {
    if (activeSources.length > 0 && (!currentDecision.source_id || !activeSources.find(s => s.id === currentDecision.source_id))) {
      setDecision(selectedComponent, 'source_id', activeSources[0].id);
    }
  }, [selectedComponent, activeSources, currentDecision.source_id, setDecision]);

  const isProcurementOpen = phase === 'procurement_open';
  const buyingCurrentComponent = isBuying[selectedComponent];

  // Specific handler for scrolling sources & snapping to min limits
  const handleSourceSelect = (sourceId: number) => {
    if (!isProcurementOpen) return;
    const newSource = activeSources.find(s => s.id === sourceId);
    if (!newSource) return;
    setDecision(selectedComponent, 'source_id', newSource.id);
    setDecision(selectedComponent, 'quantity', newSource.min_order);
  };

  const handleQuantityBlur = () => {
    if (!selectedSource) return;
    let qty = currentDecision.quantity;
    if (qty < selectedSource.min_order) qty = selectedSource.min_order;
    if (qty > selectedSource.max_order) qty = selectedSource.max_order;
    if (qty !== currentDecision.quantity) {
      setDecision(selectedComponent, 'quantity', qty);
    }
  };

  // Computations
  const totalProcurementCost = projectedCosts?.total_cost || 0;
  const currentProjections = projectedCosts?.per_component[selectedComponent];
  const componentCost = isBuying[selectedComponent] ? (currentProjections?.total || 0) : 0;

  const remainingFunds = funds - totalProcurementCost;
  const fundUsagePct = funds > 0 ? (totalProcurementCost / funds) * 100 : 100;

  let progressColor = "bg-[#3b82f6]"; // Blue for < 25%
  if (fundUsagePct >= 25 && fundUsagePct < 50) progressColor = "bg-[#10b981]"; // Green
  else if (fundUsagePct >= 50 && fundUsagePct < 75) progressColor = "bg-[#eab308]"; // Yellow
  else if (fundUsagePct >= 75) progressColor = "bg-error"; // Red

  const isOverflowing = totalProcurementCost > funds;

  const handleSubmit = async () => {
    if (!window.confirm('Confirm procurement decisions? This cannot be undone until the next phase.')) return;
    setIsSubmitting(true);
    setSubmitMessage('');
    try {
      await submitDecisions();
      const ts = new Date().toLocaleTimeString();
      setSubmitMessage(`SUCCESS: Decisions saved at ${ts}.`);
      setLastSavedAt(ts);
      addToast(`Decisions saved at ${ts}`, 'success');
    } catch (err: any) {
      setSubmitMessage(`ERROR: ${err.message || "Failed to submit"}`);
      addToast(err?.message || 'Failed to save procurement decisions', 'error');
    } finally {
      setIsSubmitting(false);
      setTimeout(() => setSubmitMessage(''), 3000);
    }
  };

  const factoryStock = components.find(c => c.component === selectedComponent)?.raw_stock;
  const renderStockGraph = () => {
    if (!factoryStock || factoryStock.length !== 101) return null;

    const unusableStock = factoryStock[0];
    const deciles = Array(25).fill(0);
    for (let i = 1; i <= 100; i++) {
      const idx = Math.min(24, Math.floor((i - 1) / 4));
      deciles[idx] += factoryStock[i];
    }
    const maxVal = Math.max(...deciles, 1);
    const totalItems = deciles.reduce((acc, curr) => acc + curr, 0);

    return (
      <div className="pt-2 flex flex-col space-y-2 relative flex-1">
        <div className="flex justify-between items-center text-[10px] text-on-surface-variant uppercase tracking-widest cursor-help group/header relative">
          <span className="flex items-center space-x-2">
            <span>Raw Stock Distribution</span>
            <span className="w-4 h-4 bg-surface-high border border-outline flex items-center justify-center rounded-full">i</span>
          </span>
          <span>Usable Units: {totalItems}</span>

          {/* Tooltip for graph */}
          <div className="absolute top-6 left-0 hidden group-hover/header:block bg-surface p-2 border border-outline-variant shadow-lg text-[10px] font-mono text-on-surface w-64 z-50 normal-case leading-relaxed">
            Displays current usable inventory density. Unusable damages (Grade 0) are excluded. New procurements will dynamically merge into this spread upon cycle resolution following transport damage rolls.
          </div>
        </div>

        <div className="flex items-end flex-1 min-h-[60px] w-full space-x-[2px] mt-1 mb-1">
          {deciles.map((val, idx) => (
            <div key={idx} className="flex-1 bg-surface-highest transition-colors flex flex-col justify-end h-full group/col relative">
              <div className="w-full bg-outline transition-all duration-300 group-hover/col:bg-primary rounded-t-sm" style={{ height: `${(val / maxVal) * 100}%` }}></div>
              <div className="absolute bottom-full mb-1 hidden group-hover/col:block bg-surface p-1 text-[10px] z-10 border border-outline-variant whitespace-nowrap shadow-lg">
                Grade {idx * 4 + 1}-{idx * 4 + 4}: {val} units
              </div>
            </div>
          ))}
        </div>
        <div className="flex justify-between text-[8px] text-on-surface-variant font-mono">
          <span>Gr 1</span>
          <span>Gr 50</span>
          <span>Gr 100</span>
        </div>

        {unusableStock > 0 && (
          <div className="text-[10px] text-error font-mono mt-1 pt-2 border-t border-error/20 flex justify-between">
            <span>UNUSABLE INVENTORY (GRADE 0)</span>
            <span className="font-bold">{unusableStock} units</span>
          </div>
        )}
      </div>
    );
  };

  const currentTransportData = transports[currentDecision.transport];

  return (
    <div className="flex flex-col h-full space-y-6">
      <ComponentTabs selected={selectedComponent} onSelect={setComponent} />

      <h1 className="font-display text-3xl uppercase tracking-tighter">
        PROCUREMENT
      </h1>

      <div className="flex space-x-6 items-center flex-shrink-0">
        <button
          onClick={() => isProcurementOpen && setIsBuying(selectedComponent, false)}
          disabled={!isProcurementOpen}
          className={`flex-1 flex items-center justify-between p-4 border font-display tracking-widest transition-colors ${!buyingCurrentComponent ? 'bg-error-container border-error text-on-surface' : 'bg-surface-low border-outline-variant text-on-surface-variant hover:bg-surface-high'} ${!isProcurementOpen && 'opacity-50 cursor-not-allowed'}`}
        >
          <span>DO NOT PURCHASE</span>
          {!buyingCurrentComponent ? <FiCheckCircle className="text-xl" /> : <FiCircle className="text-xl opacity-50" />}
        </button>

        <button
          onClick={() => isProcurementOpen && setIsBuying(selectedComponent, true)}
          disabled={!isProcurementOpen}
          className={`flex-1 flex items-center justify-between p-4 border font-display tracking-widest transition-colors ${buyingCurrentComponent ? 'bg-primary-container border-primary text-[#000]' : 'bg-surface-low border-outline-variant text-on-surface-variant hover:bg-surface-high'} ${!isProcurementOpen && 'opacity-50 cursor-not-allowed'}`}
        >
          <span>PROCURE COMPONENTS</span>
          {buyingCurrentComponent ? <FiCheckCircle className="text-xl text-[#000]" /> : <FiCircle className="text-xl opacity-50" />}
        </button>
      </div>

      {buyingCurrentComponent && (
        <div className="flex flex-1 overflow-hidden space-x-6 animate-fade-in min-h-0">
          {/* INPUT SECTION (LEFT) */}
          <div className="w-[60%] flex flex-col space-y-6 min-h-0">
            <div className="bg-surface-container p-6 space-y-6 flex-1 flex flex-col border border-outline-variant min-h-0">

              <div className="flex space-x-6 flex-shrink-0 h-[320px]">
                <div className="w-1/2 flex flex-col space-y-2 h-full">
                  <label className="block text-xs font-mono text-on-surface-variant uppercase tracking-widest flex-shrink-0">
                    SUPPLIER SOURCE
                  </label>
                  <div className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar relative">
                    {activeSources.map((s) => {
                      const isSelected = currentDecision.source_id === s.id;
                      const isSaved = initialDecisions[selectedComponent]?.source_id === s.id && initialDecisions[selectedComponent]?.quantity > 0;
                      return (
                        <div
                          key={s.id}
                          onClick={() => handleSourceSelect(s.id)}
                          className={`relative p-3 border font-mono text-xs cursor-pointer transition-colors ${isSelected ? 'bg-surface-highest border-primary' : 'bg-surface border-outline-variant hover:bg-surface-high'} ${isSaved ? 'ring-1 ring-tertiary ring-offset-1 ring-offset-surface-container' : ''}`}
                        >
                          <div className="flex justify-between items-center mb-1">
                            <span className={isSelected ? 'text-primary font-bold' : 'text-on-surface'}>{s.name}</span>
                            <span className="text-[10px] text-on-surface-variant">${s.base_cost_per_unit}/u</span>
                          </div>
                          <div className="flex justify-between text-[10px] text-on-surface-variant">
                            <span>Dist: {s.distance}km</span>
                            <span>Q: {s.quality_mean.toFixed(1)} ± {s.quality_sigma.toFixed(1)}</span>
                          </div>
                          {isSaved && <div className="absolute -top-2 -right-2 bg-tertiary text-[#000] text-[8px] px-1 font-bold">SAVED</div>}
                        </div>
                      );
                    })}
                    {activeSources.length === 0 && (
                      <div className="p-4 text-center text-on-surface-variant italic font-mono text-xs border border-outline-variant">No sources available</div>
                    )}
                  </div>
                </div>

                <div className="w-1/2 flex flex-col space-y-6 h-full overflow-y-auto custom-scrollbar pr-2">
                  {selectedSource ? (
                    <div className="bg-surface-low border border-outline-variant p-4 space-y-3 font-mono text-xs flex-1 flex flex-col">
                      <h3 className="text-primary border-b border-outline-variant/50 pb-2 mb-2 font-bold uppercase">{selectedSource.name}</h3>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">DISTANCE</span>
                        <span>{selectedSource.distance} km</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">ORDER LIMITS</span>
                        <span>{selectedSource.min_order} - {selectedSource.max_order}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">QUALITY MEAN</span>
                        <span>{selectedSource.quality_mean.toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">CONSISTENCY</span>
                        <span>±{selectedSource.quality_sigma.toFixed(2)} σ</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">UNIT BASE COST</span>
                        <span className="text-tertiary font-bold">${selectedSource.base_cost_per_unit.toFixed(2)}</span>
                      </div>

                      <div className="pt-4 border-t border-outline-variant/50 mt-auto">
                        <label className="block text-[10px] font-mono text-on-surface-variant uppercase tracking-widest mb-2">
                          PROCURING QUANTITY
                        </label>
                        <input
                          type="number"
                          min={selectedSource.min_order || 0}
                          max={selectedSource.max_order || 10000}
                          step="1"
                          value={currentDecision.quantity}
                          onBlur={handleQuantityBlur}
                          onChange={e => {
                            let val = parseInt(e.target.value) || 0;
                            setDecision(selectedComponent, 'quantity', val);
                          }}
                          disabled={!isProcurementOpen}
                          className="w-full bg-surface border border-outline-variant p-3 font-mono text-2xl text-primary"
                        />
                        {currentDecision.quantity < selectedSource.min_order || currentDecision.quantity > selectedSource.max_order ? (
                          <p className="text-error text-[10px] mt-1">Order clamped at min limits on losing focus.</p>
                        ) : null}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-surface-low border border-outline-variant p-4 flex items-center justify-center text-on-surface-variant font-mono text-xs flex-1 italic">
                      Select a source
                    </div>
                  )}
                </div>
              </div>

              {/* Transport Toggle & Projected Item Cost */}
              <div className="space-y-4 flex-shrink-0">
                <div className="space-y-2">
                  <label className="block text-xs font-mono text-on-surface-variant uppercase tracking-widest">
                    TRANSPORT MODE
                  </label>
                  <div className="flex space-x-2 relative">
                    {(Object.keys(transports) || []).map(mode => (
                      <button
                        key={mode}
                        disabled={!isProcurementOpen}
                        onClick={() => setDecision(selectedComponent, 'transport', mode)}
                        className={`flex-1 py-3 text-xs font-mono uppercase tracking-widest transition-colors border
                          ${currentDecision.transport === mode
                            ? 'bg-surface-highest text-primary border-primary ring-1 ring-primary inset-0'
                            : 'bg-surface text-on-surface-variant border-outline-variant hover:bg-surface-low'
                          }
                          ${!isProcurementOpen && 'opacity-50 cursor-not-allowed'}
                        `}
                      >
                        {mode}
                      </button>
                    ))}

                    <button
                      onClick={() => setShowTransportDetails(!showTransportDetails)}
                      className="flex items-center justify-center w-12 bg-surface-low border border-outline-variant hover:bg-surface-high transition-colors"
                    >
                      {showTransportDetails ? <FiChevronUp /> : <FiChevronDown />}
                    </button>

                    {showTransportDetails && currentTransportData && (
                      <div className="absolute right-0 bottom-full mb-2 w-72 bg-surface-highest border border-primary p-4 z-10 shadow-lg font-mono text-xs space-y-2 animate-fade-in">
                        <div className="flex justify-between items-center border-b border-outline-variant pb-2 mb-2">
                          <span className="font-bold text-primary uppercase">{currentDecision.transport} DATA</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-on-surface-variant">Base Cost</span>
                          <span>${currentTransportData.base_cost} / dispatch</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-on-surface-variant">Variable Cost</span>
                          <span>${currentTransportData.var_cost} / unit·km</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-on-surface-variant">Quality Spread Add</span>
                          <span>+{currentTransportData.sigma_add.toFixed(2)} σ</span>
                        </div>
                        <div className="flex justify-between text-error">
                          <span className="text-on-surface-variant text-error">Damage Prob.</span>
                          <span>{(currentTransportData.p_damage * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* PROJECTED COMPONENT COST INSIDE LEFT BANE */}
                {selectedSource && isBuying[selectedComponent] && currentProjections && (
                  <div className="p-4 border border-outline-variant bg-surface-highest group relative flex justify-between items-center cursor-help">
                    <span className="text-on-surface-variant font-mono text-xs uppercase tracking-widest flex items-center space-x-2">
                      <span>Projected Total Cost</span>
                      <span className="bg-primary/20 text-primary rounded-full w-4 h-4 flex items-center justify-center font-bold text-[10px]">i</span>
                    </span>
                    <span className="font-mono text-xl text-primary font-bold">
                      ${componentCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                    {/* Explicit tooltip block for hover */}
                    <div className="absolute left-1/4 bottom-full hidden group-hover:block bg-surface p-3 border border-outline-variant shadow-lg text-[10px] font-mono text-on-surface whitespace-nowrap z-50">
                      <div className="border-b border-outline-variant/30 pb-2 mb-2 font-bold uppercase tracking-widest text-primary">Cost Breakdown</div>
                      <div className="flex justify-between mb-1 space-x-6"><span className="text-on-surface-variant">Material Subtotal:</span> <span>${currentProjections.material_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
                      <div className="flex justify-between"><span className="text-on-surface-variant">Transport Subtotal:</span> <span>${currentProjections.transport_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></div>
                      <div className="border-t border-outline-variant/30 mt-2 pt-2 text-tertiary italic">External market modifiers included if applicable</div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {submitMessage && (
              <div className={`p-4 border-l-4 font-mono text-sm bg-surface-high flex-shrink-0
                ${submitMessage.startsWith('SUCCESS') ? 'text-primary border-primary' : 'text-error border-error'}`}>
                {submitMessage}
              </div>
            )}
          </div>

          {/* TOTALS & FACTORY IMPACT PANEL (RIGHT) */}
          <div className="w-[40%] flex flex-col space-y-6 min-h-0 overflow-y-auto custom-scrollbar pr-2">
            <div className="bg-surface-low p-6 border border-outline-variant space-y-6 flex-1 flex flex-col">
              <h2 className="font-display text-sm uppercase tracking-widest text-[#978d9e] border-b border-outline-variant pb-2 flex items-center justify-between group relative cursor-help">
                <span>ORDER SUMMARY</span>
                <span className="bg-surface-high text-on-surface border border-outline-variant rounded-full w-5 h-5 flex items-center justify-center font-bold text-[10px]">i</span>
                <div className="absolute right-0 top-full mt-2 hidden group-hover:block bg-surface p-3 border border-outline-variant shadow-lg text-[10px] font-mono text-on-surface w-64 z-[60] leading-relaxed font-normal normal-case">
                  Procured materials are mixed with existing inventory distributions upon cycle resolution. Unfavorable transports reduce incoming grade means or trigger damage variances over distance.
                </div>
              </h2>

              <div className="flex flex-col flex-1">
                {/* Raw Material Distribution Chart */}
                {renderStockGraph()}

                <div className="flex flex-col pt-6 mt-4 border-t border-outline-variant/30 space-y-3">
                  <div className="flex justify-between items-center group relative cursor-help">
                    <span className="flex items-center space-x-2">
                      <span className="text-on-surface-variant text-xs uppercase tracking-widest">FUND UTILISATION</span>
                      <span className="w-4 h-4 bg-surface-high border border-outline flex items-center justify-center rounded-full text-[10px]">i</span>
                    </span>
                    <span className="text-on-surface-variant text-[10px]">
                      {fundUsagePct.toFixed(1)}% of ${funds.toLocaleString()}
                    </span>
                    <div className="absolute right-0 bottom-full mb-2 hidden group-hover:block bg-surface p-2 border border-outline-variant shadow-lg text-[10px] font-mono text-on-surface w-48 z-50 normal-case leading-relaxed">
                      Tracks your global projected spend against company liquid funds dynamically updated by backend game API calculations.
                    </div>
                  </div>

                  {/* Progress Bar Container */}
                  <div className="w-full bg-surface h-3 border border-outline-variant relative overflow-hidden">
                    <div className={`h-full ${progressColor} transition-all duration-300`} style={{ width: `${Math.min(fundUsagePct, 100)}%` }} />
                    {isOverflowing && (
                      <div className="absolute inset-0 bg-error/40" style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(255,0,0,0.5) 5px, rgba(255,0,0,0.5) 10px)' }}></div>
                    )}
                  </div>

                  <div className={`flex justify-between items-end ${isOverflowing ? 'text-error font-bold' : 'text-on-surface'}`}>
                    <span className="text-[10px] uppercase">PROJECTED SURPLUS</span>
                    <span className="text-lg">
                      ${remainingFunds.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </div>

                  {isOverflowing && (
                    <div className="bg-error-container text-on-surface p-3 text-[10px] leading-relaxed border-l-2 border-error animate-pulse">
                      <strong className="block mb-1">CASH CRUNCH IMMINENT</strong>
                      Your total procurement exceeds available funds. Operational shortages are automatically resolved at year-end via mandatory short-term loans bearing punitive interest.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* BOTTOM BAR */}
      <div className="bg-surface-container border border-outline-variant p-6 flex justify-between items-center mt-auto flex-shrink-0">
        <div className="flex space-x-12 relative w-full h-full">
          <div>
            <div className="text-on-surface-variant font-display text-xs tracking-widest mb-1 flex items-center space-x-2">
              <span>GLOBAL SPEND PROJECTION</span>
              {projectedCosts ? <FiCheckCircle className="text-primary text-[10px]" /> : null}
            </div>
            <div className={`font-mono text-xl ${isOverflowing ? 'text-error' : 'text-on-surface'}`}>${totalProcurementCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            {lastSavedAt && <div className="absolute top-full mt-2 text-on-surface-variant font-mono text-[10px]">Saved at {lastSavedAt}</div>}
          </div>
        </div>

        <div className="w-64">
          <SendDecisionsButton
            onClick={handleSubmit}
            disabled={!isProcurementOpen || (buyingCurrentComponent && selectedSource && (currentDecision.quantity < selectedSource.min_order || currentDecision.quantity > selectedSource.max_order))}
            loading={isSubmitting}
          />
        </div>
      </div>
    </div>
  );
};
