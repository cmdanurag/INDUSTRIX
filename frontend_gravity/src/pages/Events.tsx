import { useEffect, useState, useMemo } from 'react';
import { useGameStore } from '../store';
import { useEventsStore } from '../store/useEventsStore';
import type {
  ProcurementSummary,
  ProcurementComponentSummary,
  ProductionSummary,
  ProductionComponentSummary,
  SalesSummary,
} from '../types';
import {
  FiPackage,
  FiSettings,
  FiTrendingUp,
  FiChevronDown,
  FiChevronUp,
  FiAlertTriangle,
  FiCheckCircle,
  FiXCircle,
  FiShield,
} from 'react-icons/fi';

// ─────────────────────────────────────────────────────────────────────────────
// Mini horizontal bar chart
// ─────────────────────────────────────────────────────────────────────────────
const MiniBar = ({ value, max, color = 'bg-primary' }: { value: number; max: number; color?: string }) => (
  <div className="flex items-center space-x-2 w-full">
    <div className="flex-1 h-[6px] bg-surface-highest rounded-full overflow-hidden">
      <div
        className={`h-full ${color} rounded-full transition-all duration-500`}
        style={{ width: `${Math.min(100, max > 0 ? (value / max) * 100 : 0)}%` }}
      />
    </div>
    <span className="text-[10px] font-mono text-on-surface-variant w-8 text-right shrink-0">{value}</span>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// Component quality histogram (50-column, grades 1–100 in pairs)
// ─────────────────────────────────────────────────────────────────────────────
const QualityHistogram = ({ raw }: { raw: number[] }) => {
  const [hovered, setHovered] = useState<number | null>(null);
  if (!raw || raw.length !== 101) return null;

  // 50 bins, each covering 2 grade points (1-2, 3-4, ... 99-100)
  const bins = Array(50).fill(0);
  for (let i = 1; i <= 100; i++) {
    const idx = Math.min(49, Math.floor((i - 1) / 2));
    bins[idx] += raw[i];
  }
  const maxVal = Math.max(...bins, 1);
  const unusable = raw[0];

  return (
    <div className="space-y-1">
      <div className="flex items-end h-[40px] w-full space-x-[1px]">
        {bins.map((val, idx) => (
          <div
            key={idx}
            className="flex-1 flex flex-col justify-end h-full relative"
            onMouseEnter={() => setHovered(idx)}
            onMouseLeave={() => setHovered(null)}
          >
            <div
              className={`w-full rounded-t-[1px] transition-all duration-300 ${hovered === idx ? 'bg-primary' : 'bg-outline'}`}
              style={{ height: `${(val / maxVal) * 100}%` }}
            />
            {hovered === idx && val > 0 && (
              <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-surface border border-outline-variant px-2 py-1 text-[9px] font-mono whitespace-nowrap z-10 shadow-lg">
                Gr {idx * 2 + 1}–{idx * 2 + 2}: {val}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="flex justify-between text-[8px] font-mono text-on-surface-variant">
        <span>Gr 1</span><span>Gr 50</span><span>Gr 100</span>
      </div>
      {unusable > 0 && (
        <div className="text-[9px] text-error font-mono flex justify-between">
          <span>Unusable (Grade 0)</span><span>{unusable} units</span>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Sabotage / Event notification banner
// ─────────────────────────────────────────────────────────────────────────────
const EventBanner = ({ event, component }: { event: string; component: string }) => {
  if (event === 'none' || !event) return null;

  const isSabotage = event === 'sabotaged';
  const isDamage = event === 'partial_damage';

  return (
    <div className={`flex items-start space-x-3 px-4 py-3 text-xs font-mono border ${
      isSabotage 
        ? 'bg-error/10 border-error/40 text-error' 
        : isDamage 
          ? 'bg-tertiary/10 border-tertiary/40 text-tertiary'
          : 'bg-surface-highest border-outline-variant text-on-surface-variant'
    }`}>
      {isSabotage ? <FiShield size={14} className="mt-0.5 shrink-0" /> : <FiAlertTriangle size={14} className="mt-0.5 shrink-0" />}
      <div className="space-y-1">
        <div className="font-bold uppercase tracking-widest">
          {isSabotage ? '⚠ SUPPLY SABOTAGE DETECTED' : isDamage ? 'PARTIAL TRANSIT DAMAGE' : event.toUpperCase()}
        </div>
        <div className="opacity-80 normal-case leading-relaxed">
          {isSabotage
            ? `Your ${component.replace('_', ' ')} shipment was compromised. A fraction of units were downgraded to unusable. If you can identify the responsible party and report to the organiser, you may be eligible for compensation and the aggressor faces penalties.`
            : isDamage
              ? `${component.replace('_', ' ')} shipment suffered partial damage in transit. A portion of units were degraded in quality due to transport conditions.`
              : `An event affected your ${component.replace('_', ' ')} procurement this cycle.`
          }
        </div>
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Procurement Summary Card
// ─────────────────────────────────────────────────────────────────────────────
const ProcurementCard = ({ data }: { data: ProcurementSummary }) => {
  const [open, setOpen] = useState(false);
  const [expandedComp, setExpandedComp] = useState<string | null>(null);

  const components = Object.entries(data.per_component || {}) as [string, ProcurementComponentSummary][];
  const totalOrdered = components.reduce((s, [, c]) => s + (c.units_ordered ?? 0), 0);
  const totalReceived = components.reduce((s, [, c]) => s + (c.units_received ?? 0), 0);
  const lossUnits = totalOrdered - totalReceived;
  const sabotaged = components.filter(([, c]) => c.event === 'sabotaged');
  const hasSabotage = sabotaged.length > 0;

  return (
    <div className={`border bg-surface-low overflow-hidden transition-all ${hasSabotage ? 'border-error/50' : 'border-outline-variant'}`}>
      {/* Sabotage alert strip */}
      {hasSabotage && (
        <div className="bg-error/10 border-b border-error/30 px-5 py-2 flex items-center space-x-2 text-error text-[10px] font-mono uppercase tracking-widest">
          <FiShield size={12} />
          <span>Supply sabotage detected on {sabotaged.length} component{sabotaged.length > 1 ? 's' : ''} — see details below</span>
        </div>
      )}

      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-highest/40 transition-colors"
      >
        <div className="flex items-center space-x-4">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${hasSabotage ? 'bg-error/10 border border-error/30 text-error' : 'bg-primary/10 border border-primary/30 text-primary'}`}>
            <FiPackage size={14} />
          </div>
          <div className="text-left">
            <div className="text-xs font-mono uppercase tracking-widest text-on-surface-variant">Cycle {data.cycle_number}</div>
            <div className="font-display text-sm uppercase tracking-wider text-on-surface">Procurement Resolution</div>
          </div>
        </div>
        <div className="flex items-center space-x-6">
          <div className="text-right">
            <div className="text-xs text-on-surface-variant font-mono">TOTAL SPENT</div>
            <div className="font-mono text-sm text-on-surface">${(data.total_cost ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
          </div>
          {lossUnits > 0 && (
            <div className="text-right">
              <div className="text-xs text-on-surface-variant font-mono">UNITS LOST</div>
              <div className="font-mono text-sm text-error">{lossUnits}</div>
            </div>
          )}
          <div className="text-right">
            <div className="text-xs text-on-surface-variant font-mono">FILL RATE</div>
            <div className={`font-mono text-sm ${totalOrdered > 0 && totalReceived < totalOrdered ? 'text-error' : 'text-primary'}`}>
              {totalOrdered > 0 ? Math.round((totalReceived / totalOrdered) * 100) : 100}%
            </div>
          </div>
          <div className="text-on-surface-variant">{open ? <FiChevronUp /> : <FiChevronDown />}</div>
        </div>
      </button>

      {/* Expanded body */}
      {open && (
        <div className="border-t border-outline-variant space-y-0">
          {/* Cost overview */}
          <div className="px-5 py-4 grid grid-cols-3 gap-4 bg-surface-highest/30 border-b border-outline-variant/30">
            <div>
              <div className="text-[10px] text-on-surface-variant uppercase tracking-widest">Total Cost</div>
              <div className="text-lg font-mono text-on-surface">${(data.total_cost ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            </div>
            <div>
              <div className="text-[10px] text-on-surface-variant uppercase tracking-widest">Total Ordered</div>
              <div className="text-lg font-mono text-on-surface">{totalOrdered.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-[10px] text-on-surface-variant uppercase tracking-widest">Total Received</div>
              <div className={`text-lg font-mono ${lossUnits > 0 ? 'text-error' : 'text-primary'}`}>{totalReceived.toLocaleString()}</div>
            </div>
          </div>

          {/* Per-component breakdown */}
          {components.map(([comp, c]) => {
            const damaged = (c.units_received ?? 0) < (c.units_ordered ?? 0);
            const isSab = c.event === 'sabotaged';
            const isExpanded = expandedComp === comp;

            return (
              <div key={comp} className={`border-b border-outline-variant/20 ${isSab ? 'bg-error/5' : ''}`}>
                {/* Component row header */}
                <button
                  onClick={() => setExpandedComp(isExpanded ? null : comp)}
                  className="w-full flex items-center justify-between px-5 py-3 hover:bg-surface-highest/30 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    {isSab && <FiShield size={12} className="text-error shrink-0" />}
                    {!isSab && c.event === 'partial_damage' && <FiAlertTriangle size={12} className="text-tertiary shrink-0" />}
                    {!isSab && c.event === 'none' && <FiCheckCircle size={12} className="text-primary shrink-0" />}
                    <span className="font-mono text-xs capitalize text-on-surface">{comp.replace('_', ' ')}</span>
                    <span className="text-[10px] text-on-surface-variant font-mono">{c.source ?? '—'}</span>
                    <span className="text-[10px] text-on-surface-variant font-mono uppercase">{c.transport ?? '—'}</span>
                    {c.distance_km != null && (
                      <span className="text-[10px] text-on-surface-variant font-mono">{c.distance_km} km</span>
                    )}
                  </div>
                  <div className="flex items-center space-x-6">
                    <div className="text-right">
                      <div className="text-[10px] text-on-surface-variant font-mono">ORDERED → RCVD</div>
                      <div className={`text-xs font-mono ${damaged ? 'text-error' : 'text-primary'}`}>
                        {c.units_ordered ?? 0} → {c.units_received ?? 0}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-on-surface-variant font-mono">COST</div>
                      <div className="text-xs font-mono text-on-surface">${(c.cost ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    </div>
                    <div className="text-on-surface-variant">{isExpanded ? <FiChevronUp size={12} /> : <FiChevronDown size={12} />}</div>
                  </div>
                </button>

                {/* Expanded component details */}
                {isExpanded && (
                  <div className="px-5 pb-5 space-y-4 border-t border-outline-variant/20">
                    {/* Event notification */}
                    <EventBanner event={c.event ?? 'none'} component={comp} />

                    {/* Fill rate bar */}
                    <div>
                      <div className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-2">Fill Rate</div>
                      <MiniBar
                        value={c.units_received ?? 0}
                        max={c.units_ordered ?? 1}
                        color={damaged ? 'bg-error' : 'bg-primary'}
                      />
                    </div>

                    {/* Quality histogram */}
                    {c.raw && (
                      <div>
                        <div className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-2">Received Quality Distribution</div>
                        <QualityHistogram raw={c.raw} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Cost breakdown table */}
          <div className="px-5 py-4 space-y-2">
            <div className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-3">Cost Breakdown</div>
            {components.map(([comp, c]) => (
              <div key={comp} className="flex items-center justify-between text-xs font-mono">
                <span className="capitalize text-on-surface-variant">{comp.replace('_', ' ')}</span>
                <div className="flex-1 mx-4">
                  <MiniBar value={c.cost ?? 0} max={data.total_cost ?? 1} color="bg-outline" />
                </div>
                <span className="text-on-surface">${(c.cost ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
              </div>
            ))}
            <div className="flex justify-between pt-2 border-t border-outline-variant font-mono text-sm">
              <span className="text-on-surface-variant uppercase tracking-widest text-xs">Total</span>
              <span className="text-on-surface font-bold">${(data.total_cost ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Production Summary Card
// ─────────────────────────────────────────────────────────────────────────────
import { NormalDistributionChart } from '../components/NormalDistributionChart';

const ProductionCard = ({ data }: { data: ProductionSummary }) => {
  const [open, setOpen] = useState(false);
  const components = Object.entries(data.components || {}) as [string, ProductionComponentSummary][];
  const totalProduced = components.reduce((s, [, c]) => s + (c.units_produced ?? 0), 0);
  const totalRequested = components.reduce((s, [, c]) => s + (c.requested ?? 0), 0);
  const hasAlert = data.riot || data.strike;

  return (
    <div className={`border bg-surface-low overflow-hidden transition-all ${hasAlert ? 'border-error/50' : 'border-outline-variant'}`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-highest/40 transition-colors"
      >
        <div className="flex items-center space-x-4">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${hasAlert ? 'bg-error/10 border border-error/30 text-error' : 'bg-tertiary/10 border border-tertiary/30 text-tertiary'}`}>
            <FiSettings size={14} />
          </div>
          <div className="text-left">
            <div className="text-xs font-mono uppercase tracking-widest text-on-surface-variant">Cycle {data.cycle_number}</div>
            <div className="font-display text-sm uppercase tracking-wider text-on-surface">Production Resolution</div>
          </div>
        </div>
        <div className="flex items-center space-x-6">
          <div className="text-right">
            <div className="text-xs text-on-surface-variant font-mono">UNITS PRODUCED</div>
            <div className="font-mono text-sm text-on-surface">
              <span className={totalProduced < totalRequested ? 'text-error' : 'text-primary'}>{totalProduced.toLocaleString()}</span>
              <span className="text-[10px] opacity-60 ml-1">/ {totalRequested.toLocaleString()}</span>
            </div>
          </div>
          {hasAlert && (
            <div className="flex items-center space-x-1 text-error text-xs font-mono">
              <FiAlertTriangle size={12} />
              <span>{data.riot ? 'RIOT' : 'STRIKE'}</span>
            </div>
          )}
          <div className="text-on-surface-variant">{open ? <FiChevronUp /> : <FiChevronDown />}</div>
        </div>
      </button>

      {open && (
        <div className="border-t border-outline-variant px-5 py-5 space-y-6">
          {/* Labour strip */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Wage Tier', value: (data.labour?.wage_level ?? '—').replace('_', ' ').toUpperCase(), sub: 'Compensation' },
              { label: 'Workforce', value: String(data.labour?.workforce_size ?? 0), sub: 'Active Staff' },
              { label: 'Skill Level', value: (data.labour?.skill_level ?? 0).toFixed(1), sub: 'Experience %' },
              { label: 'Morale', value: (data.labour?.morale ?? 0).toFixed(1), sub: 'Satisfaction' },
            ].map(({ label, value, sub }) => (
              <div key={label} className="bg-surface-highest/50 border border-outline-variant/30 p-3">
                <div className="text-[9px] text-on-surface-variant uppercase tracking-widest">{label}</div>
                <div className="text-sm font-mono text-on-surface mt-0.5 font-bold">{value}</div>
                <div className="text-[8px] font-mono text-on-surface-variant mt-1 opacity-60 italic">{sub}</div>
              </div>
            ))}
          </div>

          <div className="space-y-4">
            {components.map(([comp, c]) => {
              const cond = c.machine_condition_after ?? 100;
              const req = c.requested ?? 0;
              const prod = c.units_produced ?? 0;
              const fillRate = req > 0 ? (prod / req) * 100 : 100;
              
              const mean = c.effective_grade_mean ?? 0;
              const sigma = c.effective_sigma ?? 0;

              return (
                <div key={comp} className="bg-surface-highest/20 border border-outline-variant/40 p-4">
                  <div className="flex items-start space-x-6">
                    {/* Distribution Graph */}
                    <div className="shrink-0 bg-surface border border-outline-variant p-2">
                       <NormalDistributionChart 
                          mean={mean} 
                          sigma={sigma} 
                          width={200} 
                          height={100} 
                       />
                    </div>

                    <div className="flex-1 space-y-4 min-w-0">
                      <div className="flex justify-between items-center border-b border-outline-variant/30 pb-2">
                         <div className="flex items-center space-x-3">
                            <h3 className="font-display text-sm uppercase tracking-wider text-primary">{comp.replace('_', ' ')}</h3>
                            <span className="px-2 py-0.5 text-[9px] font-mono bg-surface-highest text-on-surface-variant uppercase border border-outline-variant/50 rounded">
                              {(c.maintenance || 'none')} Maint.
                            </span>
                         </div>
                         <div className="text-right">
                            <span className="text-[10px] font-mono text-on-surface-variant uppercase tracking-widest">Efficiency: </span>
                            <span className={`text-xs font-mono font-bold ${fillRate < 95 ? 'text-error' : 'text-primary'}`}>
                              {isFinite(fillRate) ? fillRate.toFixed(1) : '100.0'}%
                            </span>
                         </div>
                      </div>

                      <div className="grid grid-cols-4 gap-6">
                        <div className="space-y-1">
                          <div className="text-[9px] text-on-surface-variant uppercase tracking-normal">Production Vol</div>
                          <div className="text-xs font-mono text-on-surface">
                            <div className="font-bold">{prod}<span className="text-[10px] opacity-40 ml-1">RCV</span></div>
                            <div className="opacity-60">{req}<span className="text-[10px] ml-1">REQ</span></div>
                          </div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-[9px] text-on-surface-variant uppercase tracking-normal">Factory Capacity</div>
                           <div className="text-xs font-mono text-on-surface">
                              <div className="font-bold">{(c.total_throughput ?? 0)}<span className="text-[10px] opacity-40 ml-1">MAX</span></div>
                              <div className="opacity-60">{(c.machines_active ?? 0)}<span className="text-[10px] ml-1">MACH</span></div>
                           </div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-[9px] text-on-surface-variant uppercase tracking-normal">Raw Material</div>
                          <div className="text-xs font-mono text-on-surface">
                            <div className="font-bold">{(c.rm_consumed ?? 0)}<span className="text-[10px] opacity-40 ml-1">USE</span></div>
                            <div className="opacity-60">{(c.fin_stock_total ?? 0)}<span className="text-[10px] ml-1">STK</span></div>
                          </div>
                        </div>
                        <div className="space-y-1">
                           <div className="text-[9px] text-on-surface-variant uppercase tracking-normal">Quality Parameters</div>
                           <div className="text-xs font-mono text-on-surface">
                              <div className="font-bold text-primary">{mean.toFixed(1)} <span className="text-[10px] opacity-40">μ</span></div>
                              <div className="opacity-60">±{sigma.toFixed(2)} <span className="text-[10px] font-sans">σ</span></div>
                           </div>
                        </div>
                      </div>

                      <div className="pt-2">
                        <div className="flex justify-between items-center text-[10px] text-on-surface-variant uppercase mb-2">
                          <span>Machine Integrity after resolution</span>
                          <span className={`${cond < 50 ? 'text-error' : 'text-primary'}`}>{cond}%</span>
                        </div>
                        <MiniBar value={Math.round(cond)} max={100} color={cond < 40 ? 'bg-error' : cond < 70 ? 'bg-tertiary' : 'bg-primary'} />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Sales Summary Card
// ─────────────────────────────────────────────────────────────────────────────
const SalesCard = ({ data }: { data: SalesSummary }) => {
  const [open, setOpen] = useState(false);
  const brandUp = (data.brand_delta ?? 0) >= 0;
  const tiers = Object.entries(data.revenue_by_tier || {});
  const maxTierRev = Math.max(...tiers.map(([, v]) => v), 1);

  return (
    <div className="border border-outline-variant bg-surface-low overflow-hidden transition-all">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-highest/40 transition-colors"
      >
        <div className="flex items-center space-x-4">
          <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center text-primary">
            <FiTrendingUp size={14} />
          </div>
          <div className="text-left">
            <div className="text-xs font-mono uppercase tracking-widest text-on-surface-variant">Cycle {data.cycle_number}</div>
            <div className="font-display text-sm uppercase tracking-wider text-on-surface">Sales Resolution</div>
          </div>
        </div>
        <div className="flex items-center space-x-6">
          <div className="text-right">
            <div className="text-xs text-on-surface-variant font-mono">REVENUE</div>
            <div className="font-mono text-sm text-primary">${(data.revenue ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-on-surface-variant font-mono">BRAND Δ</div>
            <div className={`font-mono text-sm ${brandUp ? 'text-primary' : 'text-error'}`}>
              {brandUp ? '+' : ''}{(data.brand_delta ?? 0).toFixed(1)}
            </div>
          </div>
          {data.black_market_discovered && (
            <div className="flex items-center space-x-1 text-error text-xs font-mono">
              <FiXCircle size={12} /><span>BLACK MKT</span>
            </div>
          )}
          <div className="text-on-surface-variant">{open ? <FiChevronUp /> : <FiChevronDown />}</div>
        </div>
      </button>

      {open && (
        <div className="border-t border-outline-variant px-5 py-5 space-y-6">
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Assembled', value: String(data.drones_assembled ?? 0) },
              { label: 'Sold', value: String(data.units_sold ?? 0) },
              { label: 'Held', value: String(data.units_held ?? 0) },
              { label: 'Scrapped', value: String(data.units_scrapped ?? 0) },
            ].map(({ label, value }) => (
              <div key={label} className="bg-surface-highest p-3">
                <div className="text-[10px] text-on-surface-variant uppercase tracking-widest">{label}</div>
                <div className="text-sm font-mono text-on-surface mt-1">{value}</div>
              </div>
            ))}
          </div>

          {data.black_market_discovered && (
            <div className="flex items-center space-x-2 bg-error/10 border border-error/30 text-error px-4 py-3 text-xs font-mono">
              <FiXCircle size={14} /><span>BLACK MARKET ACTIVITY DISCOVERED — brand penalty applied, potential fine incoming.</span>
            </div>
          )}

          <div className="space-y-2">
            <div className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-3">Revenue by Tier</div>
            {tiers.map(([tier, rev]) => (
              <div key={tier} className="flex items-center space-x-3">
                <span className="text-[10px] font-mono text-on-surface-variant capitalize w-24 shrink-0">{tier}</span>
                <div className="flex-1 h-[8px] bg-surface-highest rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all duration-500" style={{ width: `${(rev / maxTierRev) * 100}%` }} />
                </div>
                <span className="text-xs font-mono text-on-surface w-20 text-right shrink-0">
                  ${rev.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
            ))}
          </div>

          {data.faction_sales && data.faction_sales.length > 0 && (
            <div className="overflow-x-auto">
              <div className="text-[10px] text-on-surface-variant uppercase tracking-widest mb-3">Faction Breakdown</div>
              <table className="w-full text-left font-mono text-xs border-collapse">
                <thead>
                  <tr className="text-on-surface-variant border-b border-outline-variant/50">
                    <th className="py-2 pr-4 font-normal uppercase tracking-widest">Faction</th>
                    <th className="py-2 pr-4 font-normal uppercase tracking-widest">Tier</th>
                    <th className="py-2 pr-4 font-normal uppercase tracking-widest text-right">Units</th>
                    <th className="py-2 pr-4 font-normal uppercase tracking-widest text-right">Price/Unit</th>
                    <th className="py-2 font-normal uppercase tracking-widest text-right">Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {data.faction_sales.map((sale, idx) => (
                    <tr key={idx} className="border-b border-outline-variant/20 hover:bg-surface-highest/30 transition-colors">
                      <td className="py-3 pr-4 text-on-surface">{sale.faction}</td>
                      <td className="py-3 pr-4 capitalize text-on-surface-variant">{sale.tier}</td>
                      <td className="py-3 pr-4 text-right text-on-surface">{sale.units_sold}</td>
                      <td className="py-3 pr-4 text-right text-on-surface-variant">${sale.price_per_unit?.toLocaleString()}</td>
                      <td className="py-3 text-right text-primary">${sale.revenue?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="grid grid-cols-3 gap-3 pt-3 border-t border-outline-variant font-mono text-xs">
            <div>
              <div className="text-on-surface-variant uppercase tracking-widest">Holding Cost</div>
              <div className="text-error text-sm">-${(data.holding_cost ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
            </div>
            <div>
              <div className="text-on-surface-variant uppercase tracking-widest">Brand Score</div>
              <div className="text-on-surface text-sm">
                {(data.brand_score_after ?? 0).toFixed(1)}
                <span className={`ml-2 text-[10px] ${brandUp ? 'text-primary' : 'text-error'}`}>
                  ({brandUp ? '+' : ''}{(data.brand_delta ?? 0).toFixed(1)})
                </span>
              </div>
            </div>
            <div>
              <div className="text-on-surface-variant uppercase tracking-widest">Closing Funds</div>
              <div className={`text-sm ${(data.closing_funds ?? 0) < 0 ? 'text-error' : 'text-on-surface'}`}>
                ${(data.closing_funds ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Pending placeholder card
// ─────────────────────────────────────────────────────────────────────────────
const PendingCard = ({ label, icon }: { label: string; icon: React.ReactNode }) => (
  <div className="border border-outline-variant/40 bg-surface-low px-5 py-4 flex items-center space-x-4 opacity-40">
    <div className="w-8 h-8 rounded-full bg-surface-highest border border-outline-variant flex items-center justify-center text-on-surface-variant">
      {icon}
    </div>
    <div>
      <div className="text-xs font-mono uppercase tracking-widest text-on-surface-variant">Pending</div>
      <div className="font-display text-sm uppercase tracking-wider text-on-surface-variant">{label}</div>
    </div>
    <div className="ml-auto text-[10px] font-mono text-on-surface-variant uppercase tracking-widest">Not yet resolved</div>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// News & Intelligence Section
// ─────────────────────────────────────────────────────────────────────────────
const IntelSection = ({ hasSabotage }: { hasSabotage: boolean }) => (
  <div className={`border p-5 mb-6 transition-all ${
    hasSabotage 
      ? 'bg-error/5 border-error/30 shadow-[0_0_20px_rgba(var(--error-rgb),0.05)]' 
      : 'bg-surface-low border-outline-variant'
  }`}>
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-[10px] font-mono text-primary uppercase tracking-[0.2em] flex items-center space-x-2">
        <FiShield size={14} className={hasSabotage ? 'text-error' : 'text-primary'} />
        <span>Intelligence & Reporting Protocol</span>
      </h2>
      {hasSabotage && (
        <div className="flex items-center space-x-2 bg-error/20 px-2 py-1 rounded text-[9px] font-bold text-error animate-pulse">
          <FiAlertTriangle size={10} />
          <span>SECURITY BREACH DETECTED</span>
        </div>
      )}
    </div>
    
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-mono leading-relaxed">
      <div className="space-y-2">
        <div className="text-on-surface-variant uppercase text-[10px] tracking-widest border-b border-outline-variant/30 pb-1">Counter-Intelligence Rule</div>
        <p className="text-on-surface">
          Sabotage is an offline mechanic. If your reports show "Sabotaged" units, another team or the organiser has interfered with your supply chain.
        </p>
      </div>
      <div className="space-y-2">
        <div className="text-on-surface-variant uppercase text-[10px] tracking-widest border-b border-outline-variant/30 pb-1">Restitution Protocol</div>
        <p className="text-on-surface">
          Correctly identify the aggressor team to the Organiser during the <span className="text-primary font-bold">Backroom Phase</span>. 
          Validated reports result in <span className="text-primary">full compensation</span> for your losses and <span className="text-error font-bold">heavy fines</span> for the aggressor.
        </p>
      </div>
    </div>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// Main Events Page
// ─────────────────────────────────────────────────────────────────────────────
export const Events = () => {
  const { phase, cycleNumber } = useGameStore();
  
  const procurement = useEventsStore(s => s.procurement);
  const production = useEventsStore(s => s.production);
  const sales = useEventsStore(s => s.sales);
  const loadingProcurement = useEventsStore(s => s.loadingProcurement);
  const loadingProduction = useEventsStore(s => s.loadingProduction);
  const loadingSales = useEventsStore(s => s.loadingSales);
  const fetchAll = useEventsStore(s => s.fetchAll);

  const canSeeProcurement = ['production_open', 'sales_open', 'backroom', 'game_over'].includes(phase);
  const canSeeProduction  = ['sales_open', 'backroom', 'game_over'].includes(phase);
  const canSeeSales       = ['backroom', 'game_over'].includes(phase);

  useEffect(() => {
    fetchAll(phase);
  }, [phase, fetchAll]);

  const hasSabotage = useMemo(() => {
    if (!procurement) return false;
    return Object.values(procurement.per_component).some(c => c.event === 'sabotaged');
  }, [procurement]);

  return (
    <div className="flex flex-col h-full space-y-6">
      <div className="flex justify-between items-start flex-shrink-0">
        <div>
          <h1 className="font-display text-4xl uppercase tracking-tighter">EVENTS HUB</h1>
          <div className="text-on-surface-variant font-mono text-xs mt-1 tracking-widest flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span>Facility Cycle {cycleNumber} · Status Reports Classified</span>
          </div>
        </div>
        <button
          onClick={() => fetchAll(phase)}
          className="flex items-center space-x-2 text-xs font-mono text-on-surface-variant border border-outline-variant px-4 py-2 hover:bg-surface-highest hover:text-on-surface transition-all uppercase tracking-widest"
        >
          <FiCheckCircle size={12} />
          <span>Sync Data</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto pb-8 custom-scrollbar">
        {/* Intelligence Overlay */}
        <IntelSection hasSabotage={hasSabotage} />

        <div className="space-y-4">
          <h2 className="text-[10px] font-mono text-on-surface-variant uppercase tracking-[0.3em] pl-1">Resolution Reports</h2>
          
          {/* Procurement */}
          {canSeeProcurement ? (
            loadingProcurement ? (
              <div className="text-xs font-mono text-on-surface-variant animate-pulse px-5 py-8 border border-outline-variant/20 bg-surface-low items-center justify-center flex">
                Decrypting procurement summary...
              </div>
            ) : procurement ? (
              <ProcurementCard data={procurement} />
            ) : (
              <div className="text-xs font-mono text-on-surface-variant px-5 py-8 border border-outline-variant/20 bg-surface-low opacity-60">
                Procurement summary payload not found for this cycle.
              </div>
            )
          ) : (
            <PendingCard label="Procurement Resolution" icon={<FiPackage size={14} />} />
          )}

          {/* Production */}
          {canSeeProduction ? (
            loadingProduction ? (
              <div className="text-xs font-mono text-on-surface-variant animate-pulse px-5 py-8 border border-outline-variant/20 bg-surface-low items-center justify-center flex">
                Decrypting production summary...
              </div>
            ) : production ? (
              <ProductionCard data={production} />
            ) : (
              <div className="text-xs font-mono text-on-surface-variant px-5 py-8 border border-outline-variant/20 bg-surface-low opacity-60">
                Production summary payload not found for this cycle.
              </div>
            )
          ) : (
            <PendingCard label="Production Resolution" icon={<FiSettings size={14} />} />
          )}

          {/* Sales */}
          {canSeeSales ? (
            loadingSales ? (
              <div className="text-xs font-mono text-on-surface-variant animate-pulse px-5 py-8 border border-outline-variant/20 bg-surface-low items-center justify-center flex">
                Decrypting sales summary...
              </div>
            ) : sales ? (
              <SalesCard data={sales} />
            ) : (
              <div className="text-xs font-mono text-on-surface-variant px-5 py-8 border border-outline-variant/20 bg-surface-low opacity-60">
                Sales summary payload not found for this cycle.
              </div>
            )
          ) : (
            <PendingCard label="Sales Resolution" icon={<FiTrendingUp size={14} />} />
          )}

          {/* Empty state */}
          {phase === 'procurement_open' && !loadingProcurement && !procurement && (
            <div className="flex flex-col items-center justify-center py-20 space-y-4 text-center border border-dashed border-outline-variant">
              <div className="text-5xl opacity-20 filter grayscale">📋</div>
              <div className="space-y-1">
                <div className="font-display text-sm uppercase tracking-[0.2em] text-on-surface">No Cycle Data Yet</div>
                <div className="text-xs font-mono text-on-surface-variant opacity-60 max-w-xs mx-auto">
                  Resolution reports are compiled once the procurement phase concludes.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
