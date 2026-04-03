import { useEffect, useMemo, useState } from 'react';
import { useProcurementStore, useGameStore, useInventoryStore } from '../store';
import { useNotificationStore } from '../store/useNotificationStore';
import { ComponentTabs, SendDecisionsButton, WarningBanner } from '../components/SharedComponents';

export const Procurement = () => {
  const { 
    decisions, 
    sources, 
    selectedComponent, 
    setComponent, 
    setDecision, 
    fetchSources, 
    fetchExistingDecisions, 
    submitDecisions 
  } = useProcurementStore();

  const { phase } = useGameStore();
  const { funds, fetchInventory, rawMaterialStocks } = useInventoryStore();
  const { addToast } = useNotificationStore();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState('');
  const [lastSavedAt, setLastSavedAt] = useState('');

  // Initial data load
  useEffect(() => {
    fetchSources();
    fetchInventory();
    fetchExistingDecisions();
  }, [fetchSources, fetchInventory, fetchExistingDecisions]);

  const currentDecision = decisions[selectedComponent];
  const activeSources = sources; // Or filter if sources are component-specific in backend
  const selectedSource = activeSources.find(s => s.id === currentDecision.source_id) || activeSources[0];

  // Helper limits and cost multipliers
  const transportMults = { road: 1.0, rail: 1.4, air: 2.5 };
  
  // Computations
  const componentCost = selectedSource 
    ? currentDecision.quantity * selectedSource.base_cost_per_unit * transportMults[currentDecision.transport]
    : 0;

  const totalProcurementCost = useMemo(() => {
    let total = 0;
    // Iterate over the keys we explicitly initialized
    for (const comp of Object.keys(decisions) as Array<keyof typeof decisions>) {
      const dec = decisions[comp];
      const src = sources.find(s => s.id === dec.source_id);
      if (src) {
        total += dec.quantity * src.base_cost_per_unit * transportMults[dec.transport];
      }
    }
    return total;
  }, [decisions, sources]);

  const remainingFunds = funds - totalProcurementCost;
  const isProcurementOpen = phase === 'procurement_open';

  // Warnings
  let warningMsg = null;
  if (totalProcurementCost > funds) {
    warningMsg = "⚠ OVERSPENDING: Total cost exceeds balance";
  } else if (totalProcurementCost > 0.8 * funds) {
    warningMsg = "⚠ Spending exceeds 80% of available funds";
  }

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
    } catch(err: any) {
      setSubmitMessage(`ERROR: ${err.message || "Failed to submit"}`);
      addToast(err?.message || 'Failed to save procurement decisions', 'error');
    } finally {
      setIsSubmitting(false);
      setTimeout(() => setSubmitMessage(''), 3000);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-6">
      <ComponentTabs selected={selectedComponent} onSelect={setComponent} />
      
      <h1 className="font-display text-3xl uppercase tracking-tighter">
        PROCUREMENT
      </h1>

      <div className="flex flex-1 overflow-hidden space-x-6">
        {/* INPUT SECTION */}
        <div className="w-3/5 flex flex-col space-y-6">
          
          <div className="bg-surface-container p-6 space-y-6 flex-1 border border-outline-variant">
            {/* Supplier Select */}
            <div className="space-y-2">
              <label className="block text-xs font-mono text-on-surface-variant uppercase tracking-widest">
                SUPPLIER SOURCE
              </label>
              <div className="max-h-40 overflow-y-auto border border-outline-variant">
                <table className="w-full font-mono text-xs">
                  <thead className="bg-surface-low text-on-surface-variant">
                    <tr>
                      <th className="p-2 text-left">Supplier</th>
                      <th className="p-2 text-left">Q</th>
                      <th className="p-2 text-left">σ</th>
                      <th className="p-2 text-left">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeSources.map((s) => (
                      <tr
                        key={s.id}
                        onClick={() => isProcurementOpen && setDecision(selectedComponent, 'source_id', s.id)}
                        className={`${currentDecision.source_id === s.id ? 'bg-surface-highest' : 'bg-surface'} cursor-pointer`}
                      >
                        <td className="p-2">{s.name}</td>
                        <td className="p-2">{s.quality_mean.toFixed(2)}</td>
                        <td className="p-2">{s.quality_sigma.toFixed(2)}</td>
                        <td className="p-2">${s.base_cost_per_unit.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quantity Input */}
            <div className="space-y-2 w-1/2">
              <label className="block text-xs font-mono text-on-surface-variant uppercase tracking-widest">
                PROCURING QUANTITY
              </label>
              <input 
                type="number"
                min="0"
                max="10000"
                step="1"
                value={currentDecision.quantity}
                onChange={e => setDecision(selectedComponent, 'quantity', parseInt(e.target.value) || 0)}
                disabled={!isProcurementOpen}
                className="w-full bg-surface-low border border-outline-variant p-3 font-mono text-2xl text-primary"
              />
            </div>

            {/* Transport Toggle */}
            <div className="space-y-2">
              <label className="block text-xs font-mono text-on-surface-variant uppercase tracking-widest">
                TRANSPORT MODE
              </label>
              <div className="flex space-x-2">
                {['road', 'rail', 'air'].map(mode => (
                  <button
                    key={mode}
                    disabled={!isProcurementOpen}
                    onClick={() => setDecision(selectedComponent, 'transport', mode)}
                    className={`flex-1 py-3 text-sm font-mono uppercase tracking-widest transition-colors border
                      ${currentDecision.transport === mode 
                        ? 'bg-surface-highest text-primary border-primary' 
                        : 'bg-surface text-on-surface-variant border-outline-variant hover:bg-surface-low'
                      }
                      ${!isProcurementOpen && 'opacity-50 cursor-not-allowed'}
                    `}
                  >
                    {mode} · {transportMults[mode as keyof typeof transportMults]}x
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-on-surface-variant font-mono">Road: 20% partial / 5% total loss · Rail: 12% / 3% · Air: 5% / 1%</p>
            </div>

          </div>

          {warningMsg && <WarningBanner message={warningMsg} />}
          {submitMessage && (
            <div className={`p-4 border-l-4 font-mono text-sm bg-surface-high 
              ${submitMessage.startsWith('SUCCESS') ? 'text-primary border-primary' : 'text-error border-error'}`}>
              {submitMessage}
            </div>
          )}
        </div>

        {/* DETAILS PANEL */}
        <div className="w-2/5 flex flex-col space-y-6">
          <div className="bg-surface-low p-6 border border-outline-variant space-y-6 flex-1">
            <h2 className="font-display text-sm uppercase tracking-widest text-[#978d9e] border-b border-outline-variant pb-2">
              SUPPLY CONTRACT DETAILS
            </h2>
            
            {selectedSource && (
              <div className="space-y-4 font-mono text-sm">
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">SUPPLIER</span>
                  <span className="text-on-surface">{selectedSource.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">QUALITY MEAN</span>
                  <span className="text-on-surface">{selectedSource.quality_mean.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">CONSISTENCY</span>
                  <span className="text-on-surface">±{selectedSource.quality_sigma.toFixed(2)} σ</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">UNIT BASE COST</span>
                  <span className="text-on-surface">${selectedSource.base_cost_per_unit.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-on-surface-variant">CURRENT STOCK</span>
                  <span className="text-on-surface">{rawMaterialStocks[selectedComponent] || 0} units</span>
                </div>
              </div>
            )}
            
            <div className="pt-4 mt-4 border-t border-outline-variant space-y-4 font-mono">
              <div className="flex flex-col">
                <span className="text-on-surface-variant text-xs mb-1">THIS COMPONENT COST</span>
                <span className="text-2xl text-on-surface">${componentCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
              
              <div className="flex flex-col pt-4 border-t border-outline-variant/30">
                <span className="text-on-surface-variant text-xs mb-1">REMAINING GLOBAL FUNDS</span>
                <span className={`text-xl ${remainingFunds < 0 ? 'text-error' : 'text-primary'}`}>
                  ${remainingFunds.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM BAR */}
      <div className="bg-surface-container border border-outline-variant p-6 flex justify-between items-center">
        <div className="flex space-x-12">
          <div>
            <div className="text-on-surface-variant font-display text-xs tracking-widest mb-1">TOTAL PROCUREMENT SPEND</div>
            <div className="text-on-surface font-mono text-xl">${totalProcurementCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            {lastSavedAt && <div className="text-on-surface-variant font-mono text-xs mt-1">Last saved at {lastSavedAt}</div>}
          </div>
        </div>
        
        <div className="w-64">
          <SendDecisionsButton 
            onClick={handleSubmit} 
            disabled={!isProcurementOpen} 
            loading={isSubmitting} 
          />
        </div>
      </div>
    </div>
  );
};
