import { useEffect } from 'react';
import { useInventoryStore, useGameStore } from '../store';
import { MetricCard } from '../components/SharedComponents';
import type { ComponentType } from '../types';

export const Inventory = () => {
  const { phase } = useGameStore();
  const { 
    funds, brandScore, brandTier, droneStockTotal, droneBreakdown, rawMaterialStocks, producedThisCycle, carriedFromPrevious, hasGovLoan,
    fetchInventory, scrapRejectUnits 
  } = useInventoryStore();

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory, phase]); // Refetch when phase switches

  const holdingUnits = droneBreakdown.standard + droneBreakdown.premium;
  const holdingCost = holdingUnits * 40;

  return (
    <div className="flex flex-col h-full space-y-8">
      <h1 className="font-display text-4xl uppercase tracking-tighter">
        INVENTORY & LOGISTICS
      </h1>

      <div className="grid grid-cols-2 gap-6 w-full max-w-4xl">
        <div className="bg-surface-container p-6 flex flex-col justify-between">
          <div className="text-on-surface-variant text-xs font-display uppercase tracking-widest mb-4">GLOBAL FUNDS</div>
          <div className={`font-display text-4xl ${funds < 0 ? 'text-error' : 'text-on-surface'}`}>
            ${funds.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="text-on-surface-variant text-xs mt-2">CR</div>
        </div>
        <MetricCard 
          label="BRAND SCORE" 
          value={brandScore.toFixed(1)} 
          subtext={brandTier.toUpperCase()}
        />
      </div>

      <div className="flex flex-col lg:flex-row space-y-6 lg:space-y-0 lg:space-x-8 max-w-6xl">
        
        {/* RAW MATERIALS */}
        <div className="flex-1 bg-surface-low border border-outline-variant p-6 h-full flex flex-col">
          <h2 className="font-display text-sm uppercase tracking-widest text-[#978d9e] border-b border-outline-variant pb-2 mb-4">
            RAW MATERIALS STOCK
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-sm">
              <thead>
                <tr className="text-on-surface-variant text-xs border-b border-outline-variant">
                  <th className="py-2 font-normal text-left pl-2">COMPONENT</th>
                  <th className="py-2 font-normal text-right pr-2">UNITS</th>
                </tr>
              </thead>
              <tbody>
                {(Object.keys(rawMaterialStocks) as ComponentType[]).map((comp, idx) => (
                  <tr key={comp} className={`${idx % 2 === 0 ? 'bg-surface-highest/20' : ''} hover:bg-surface-highest/50 transition-colors`}>
                    <td className="py-3 pl-2 text-on-surface capitalize">{comp.replace('_', ' ')}</td>
                    <td className="py-3 pr-2 text-right">{rawMaterialStocks[comp]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* FINISHED DRONES */}
        <div className="flex-1 flex flex-col space-y-4">
          <div className="bg-surface-container border border-outline-variant p-6 flex flex-col">
            <h2 className="font-display text-sm uppercase tracking-widest text-[#978d9e] border-b border-outline-variant pb-2 mb-4">
              FINISHED DRONES
            </h2>
            <div className="font-display text-2xl text-on-surface mb-6 bg-surface-highest p-4 flex justify-between">
              <span>TOTAL UNITS</span>
              <span>{droneStockTotal.toLocaleString()}</span>
            </div>
            <div className="font-mono text-xs text-on-surface-variant mb-4">
              Produced this cycle: {producedThisCycle.toLocaleString()} · Carried from previous: {carriedFromPrevious.toLocaleString()}
            </div>

            <div className="space-y-2 font-mono text-sm">
              <div className="flex justify-between py-2 border-b border-outline-variant/30">
                <span className="text-error">Reject</span>
                <span>{droneBreakdown.reject.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-outline-variant/30">
                <span className="text-on-surface-variant">Substandard</span>
                <span>{droneBreakdown.substandard.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-outline-variant/30">
                <span className="text-on-surface-variant">Standard</span>
                <span>{droneBreakdown.standard.toLocaleString()}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-primary">Premium</span>
                <span>{droneBreakdown.premium.toLocaleString()}</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => scrapRejectUnits()}
            disabled={droneBreakdown.reject === 0}
            className={`w-full py-5 px-4 font-display font-bold uppercase tracking-widest border transition-all text-sm
              ${(droneBreakdown.reject === 0) 
                ? 'bg-surface-low border-outline-variant text-on-surface-variant opacity-50 cursor-not-allowed' 
                : 'bg-error/10 border-error text-error hover:bg-error hover:text-surface'}
            `}
          >
            SCRAP REJECT UNITS
          </button>
          {holdingUnits > 0 && (
            <div className="bg-surface-low border border-outline-variant p-3 font-mono text-xs text-on-surface-variant">
              Holding cost: 40 CU per unsold drone per cycle. Current holding cost: {holdingCost.toLocaleString()} CU.
            </div>
          )}
          {funds < 0 && (
            <div className="bg-surface-low border border-error p-3 font-mono text-xs text-error">
              NEGATIVE — contact organiser
            </div>
          )}
          {hasGovLoan && (
            <div className="bg-surface-low border border-outline-variant p-3 font-mono text-xs text-on-surface-variant">
              GOVERNMENT LOAN ACTIVE — backroom deals blocked. Brand score penalty active.
            </div>
          )}
        </div>
        
      </div>
    </div>
  );
};
