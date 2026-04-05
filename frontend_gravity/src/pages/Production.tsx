import { useEffect, useState, useMemo } from 'react';
import { useProductionStore, useGameStore, useInventoryStore } from '../store';
import { useNotificationStore } from '../store/useNotificationStore';
import { ComponentTabs, SendDecisionsButton } from '../components/SharedComponents';
import type { ComponentType } from '../types';
import {
  FiSettings, FiTool, FiTrendingUp, FiUsers, FiCpu, FiPlusCircle,
  FiAlertCircle, FiZap, FiPlus, FiLock, FiChevronDown, FiPlusSquare, FiX,
  FiBarChart2, FiInfo, FiDollarSign
} from 'react-icons/fi';

import {
  MACHINE_TIERS,
  MAINTENANCE_COSTS,
  WAGE_COSTS,
  AUTOMATION_UPGRADE_COST,
  RND_COST_PER_LEVEL,
  AUTOMATION_LABOUR_MULT
} from '../constants/production';

import {
  calculateProjectedCondition,
  calculateMoraleDelta,
  calculateProjectedSigma,
  calculateEffectiveGrade
} from '../utils/productionCalculations';

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

const Tooltip = ({ text, title }: { text: string; title?: string }) => (
  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-64 hidden group-hover:block z-50 bg-surface-highest border border-outline-variant p-3 shadow-2xl animate-in fade-in slide-in-from-bottom-2 pointer-events-none">
    {title && <div className="text-[10px] font-mono text-primary uppercase mb-1 font-bold tracking-widest">{title}</div>}
    <p className="text-[10px] font-mono text-on-surface leading-relaxed opacity-90 normal-case">{text}</p>
    <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-outline-variant"></div>
  </div>
);

const HealthBar = ({ current, projected, label }: { current: number, projected: number, label?: string }) => {
  const isRecovery = projected > current;
  const delta = Math.abs(projected - current);

  return (
    <div className="space-y-1">
      {label && <div className="flex justify-between text-xs uppercase tracking-widest text-on-surface-variant font-mono">
        <span className="flex items-center space-x-1">
            <span>{label}</span>
            <div className="group relative">
                <FiInfo size={10} className="text-on-surface-variant" />
                <Tooltip text="Indicates the structural integrity of this machine. Maintenance protocol affects the rate of decay per cycle." />
            </div>
        </span>
        <span className={projected < 40 ? 'text-error font-bold' : 'text-on-surface font-bold'}>{projected.toFixed(1)}%</span>
      </div>}
      <div className="h-2.5 w-full bg-surface-highest rounded-full overflow-hidden relative border border-outline-variant/30">
        <div
          className={`h-full transition-all duration-500 rounded-full ${current > 70 ? 'bg-primary' : current > 40 ? 'bg-tertiary' : 'bg-error'}`}
          style={{ width: `${current}%` }}
        />
        {isRecovery ? (
          <div 
            className="absolute top-0 h-full bg-primary/40 animate-pulse"
            style={{ left: `${current}%`, width: `${delta}%` }}
          />
        ) : (
          <div 
            className="absolute top-0 h-full bg-black/40"
            style={{ left: `${projected}%`, width: `${delta}%` }}
          />
        )}
      </div>
    </div>
  );
};

const MetricBox = ({ label, value, subvalue, icon: Icon, color = 'text-primary', tooltip }: any) => (
  <div className="bg-surface-low border border-outline-variant p-4 flex items-start space-x-4 group relative cursor-help">
    <div className={`p-2.5 rounded-lg bg-surface-highest ${color} border border-outline-variant/50 flex-shrink-0`}>
      <Icon size={22} />
    </div>
    <div className="min-w-0 flex-1">
      <div className="text-xs uppercase tracking-widest text-on-surface-variant font-mono mb-0.5">{label}</div>
      <div className="text-2xl font-display text-on-surface leading-tight truncate">{value}</div>
      {subvalue && <div className="text-[11px] font-mono text-on-surface-variant mt-0.5 opacity-80">{subvalue}</div>}
    </div>
    {tooltip && <Tooltip text={tooltip} title={label} />}
  </div>
);

const StockHistogram = ({ stock, label }: { stock: number[] | undefined, label: string }) => {
    if (!stock || stock.length !== 101) return <div className="h-24 flex items-center justify-center border border-dashed border-outline-variant text-[10px] uppercase font-mono opacity-50">Assembly Buffer Empty</div>;

    const unusableStock = stock[0];
    const deciles = Array(25).fill(0);
    for (let i = 1; i <= 100; i++) {
        const idx = Math.min(24, Math.floor((i - 1) / 4));
        deciles[idx] += stock[i];
    }
    const maxVal = Math.max(...deciles, 1);
    const totalItems = deciles.reduce((acc, curr) => acc + curr, 0);

    return (
        <div className="pt-2 flex flex-col space-y-2 relative flex-1">
            <div className="flex justify-between items-center text-[10px] text-on-surface-variant uppercase tracking-widest font-mono">
                <span className="flex items-center space-x-1">
                    <span>{label}</span>
                    <div className="group relative">
                        <FiInfo size={10} className="text-on-surface-variant" />
                        <Tooltip text="Histogram representing the quality distribution (Grade 1-100) of currently stored finished components." />
                    </div>
                </span>
                <span>Ready: {totalItems}</span>
            </div>

            <div className="flex items-end h-[60px] w-full space-x-[1px] mt-1 mb-1">
                {deciles.map((val, idx) => (
                    <div key={idx} className="flex-1 bg-surface-highest transition-colors flex flex-col justify-end h-full group/col relative">
                        <div className="w-full bg-primary/60 transition-all duration-300 group-hover/col:bg-primary rounded-t-sm" style={{ height: `${(val / maxVal) * 100}%` }}></div>
                        <div className="absolute bottom-full mb-1 hidden group-hover/col:block bg-surface p-1 text-[9px] font-mono z-10 border border-outline-variant whitespace-nowrap shadow-lg text-primary">
                            Gr {idx * 4 + 1}-{idx * 4 + 4}: {val}u
                        </div>
                    </div>
                ))}
            </div>
            <div className="flex justify-between text-[8px] text-on-surface-variant font-mono opacity-50">
                <span>Grade 1</span>
                <span>Grade 100</span>
            </div>

            {unusableStock > 0 && (
                <div className="text-[10px] text-error font-mono mt-1 pt-1 border-t border-error/20 flex justify-between">
                    <span>SCRAPPED (GRADE 0)</span>
                    <span className="font-bold">{unusableStock}u</span>
                </div>
            )}
        </div>
    );
};

const ProductionDropdown = ({ 
  label, 
  value, 
  options, 
  onChange, 
  disabled,
  tooltip
}: { 
  label: string, 
  value: string, 
  options: { value: string; label: string; info: string; cost?: number }[], 
  onChange: (v: any) => void,
  disabled: boolean,
  tooltip?: string
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selected = options.find(o => o.value === value) || options[0];

  return (
    <div className="space-y-2">
      <div className="flex items-center space-x-1">
        <label className="text-xs font-mono text-on-surface-variant uppercase tracking-widest">{label}</label>
        {tooltip && <div className="group relative"><FiInfo size={10} className="text-on-surface-variant" /><Tooltip text={tooltip} /></div>}
      </div>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled}
          className={`w-full flex items-center justify-between bg-surface border p-3.5 font-mono text-xs uppercase transition-all ${
            isOpen ? 'border-primary shadow-[0_0_15px_rgba(var(--primary-rgb),0.1)]' : 'border-outline-variant/30 hover:border-outline-variant'
          }`}
        >
          <span className="text-on-surface font-bold tracking-wider">{selected.label}</span>
          <div className="flex items-center space-x-3">
            {selected.cost !== undefined && <span className="text-on-surface-variant opacity-70">${selected.cost.toLocaleString()}</span>}
            <FiChevronDown className={`transition-transform duration-300 ${isOpen ? 'rotate-180 text-primary' : 'text-on-surface-variant'}`} />
          </div>
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-surface-low border border-primary shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-1">
            {options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => { onChange(opt.value); setIsOpen(false); }}
                className={`w-full p-4 text-left border-b border-outline-variant/20 last:border-0 hover:bg-primary/5 transition-colors group ${
                  value === opt.value ? 'bg-primary/10' : ''
                }`}
              >
                <div className="flex justify-between items-center mb-1.5">
                  <span className={`text-xs font-bold uppercase transition-colors ${value === opt.value ? 'text-primary' : 'text-on-surface group-hover:text-primary'}`}>
                    {opt.label}
                  </span>
                  {opt.cost !== undefined && <span className="text-xs font-mono text-on-surface-variant opacity-70">${opt.cost.toLocaleString()}</span>}
                </div>
                <p className="text-[11px] font-mono text-on-surface-variant leading-relaxed opacity-80 group-hover:opacity-100">
                  {opt.info}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const DiscreteStepBar = ({ 
  label, 
  currentLevel, 
  projectedLevel,
  maxLevels, 
  isUpgradeLocked, 
  cost,
  onAdd, 
  disabled,
  info,
  tooltip
}: { 
  label: string, 
  currentLevel: number, 
  projectedLevel: number,
  maxLevels: number, 
  isUpgradeLocked: boolean, 
  cost?: number,
  onAdd: () => void, 
  disabled: boolean,
  info?: string,
  tooltip?: string
}) => {
  const isDecisionMade = projectedLevel > currentLevel;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-end">
        <div className="space-y-0.5">
          <div className="flex items-center space-x-1">
            <label className="text-xs font-mono text-on-surface-variant uppercase tracking-widest">{label}</label>
            {tooltip && <div className="group relative"><FiInfo size={10} className="text-on-surface-variant" /><Tooltip text={tooltip} /></div>}
          </div>
          {info && <div className="text-[10px] font-mono text-on-surface-variant opacity-60 italic">{info}</div>}
        </div>
        <div className="text-xs font-mono text-on-surface font-bold">Lvl {currentLevel}/{maxLevels}</div>
      </div>
      
      <div className="flex items-center space-x-5">
        <div className="flex-1 flex items-center space-x-1 relative h-6">
          <div className="absolute left-0 right-0 h-[2px] bg-outline-variant/30 top-1/2 -translate-y-1/2" />
          <div 
            className="absolute left-0 h-[2px] bg-primary top-1/2 -translate-y-1/2 transition-all duration-700" 
            style={{ width: `${(currentLevel / maxLevels) * 100}%` }} 
          />
          {isDecisionMade && (
            <div 
              className="absolute h-[2px] bg-primary/40 top-1/2 -translate-y-1/2 transition-all duration-300 animate-pulse border-b border-t border-dashed border-primary/60" 
              style={{ left: `${(currentLevel / maxLevels) * 100}%`, width: `${(1 / maxLevels) * 100}%` }} 
            />
          )}
          {Array.from({ length: maxLevels + 1 }).map((_, i) => (
            <div 
              key={i}
              className={`z-10 w-3 h-3 rounded-full border-2 transition-all duration-500 transform ${
                i <= currentLevel 
                  ? 'bg-primary border-primary shadow-[0_0_12px_rgba(var(--primary-rgb),0.5)] scale-110' 
                  : i === projectedLevel
                  ? 'bg-primary/30 border-primary/60 border-dashed animate-pulse scale-105'
                  : 'bg-surface border-outline-variant/50'
              }`}
              style={{ position: 'absolute', left: `${(i / maxLevels) * 100}%`, marginLeft: i === maxLevels ? '-12px' : i === 0 ? '0' : '-6px' }}
            />
          ))}
        </div>

        <div className="flex-shrink-0 group relative">
          <button
            onClick={onAdd}
            disabled={disabled || isUpgradeLocked || (currentLevel >= maxLevels && !isDecisionMade)}
            className={`p-2 rounded-md border transition-all ${
              isUpgradeLocked 
                ? 'bg-tertiary/10 border-tertiary/40 text-tertiary cursor-not-allowed' 
                : isDecisionMade
                ? 'bg-primary/20 border-primary text-primary shadow-[0_0_10px_rgba(var(--primary-rgb),0.25)]'
                : currentLevel >= maxLevels
                ? 'bg-surface-highest border-outline-variant/20 text-on-surface-variant cursor-not-allowed opacity-30'
                : 'bg-surface border-outline-variant text-on-surface hover:bg-primary/10 hover:border-primary hover:text-primary'
            }`}
          >
            {isUpgradeLocked ? <FiLock size={16} /> : isDecisionMade ? <FiX size={16} /> : <FiPlus size={16} />}
            {isUpgradeLocked && <Tooltip title="Upgrade Locked" text="Hardware evolution in progress. Completion expected at the end of the next cycle." />}
          </button>
          {!isUpgradeLocked && currentLevel < maxLevels && cost && (
            <div className={`absolute -bottom-5 right-0 text-[10px] font-mono transition-opacity whitespace-nowrap ${isDecisionMade ? 'text-primary' : 'text-on-surface-variant opacity-0 group-hover:opacity-100'}`}>
              {isDecisionMade ? `Allocated: $${cost.toLocaleString()}` : `Cost: $${cost.toLocaleString()}`}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const BottleneckSlider = ({ 
  label, 
  value, 
  onChange, 
  throughputLimit, 
  stockLimit,
  disabled 
}: { 
  label: string, 
  value: number | null, 
  onChange: (v: number | null) => void,
  throughputLimit: number,
  stockLimit: number,
  disabled: boolean
}) => {
  const maxPossible = Math.min(throughputLimit, stockLimit);
  const isStockBottleneck = stockLimit < throughputLimit;
  const currentVal = value === null ? maxPossible : value;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-end">
        <div className="flex items-center space-x-1">
            <label className="text-xs font-mono text-on-surface-variant uppercase tracking-widest">{label}</label>
            <div className="group relative"><FiInfo size={10} className="text-on-surface-variant" /><Tooltip text="Target number of components to produce this cycle. Limited by both machine capacity and raw material stock." /></div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-display text-on-surface">{currentVal.toLocaleString()}</div>
          <div className={`text-[10px] font-mono uppercase tracking-widest font-bold ${isStockBottleneck ? 'text-tertiary' : 'text-primary'}`}>
            Max Plan: {maxPossible.toLocaleString()} · {isStockBottleneck ? 'RESOURCE LIMITED' : 'CAPACITY LIMITED'}
          </div>
        </div>
      </div>
      <div className="relative pt-2">
        <input 
          type="range"
          min="0"
          max={maxPossible || 1}
          value={currentVal}
          onChange={(e) => onChange(parseInt(e.target.value))}
          disabled={disabled || maxPossible === 0}
          className="w-full h-2 bg-surface-highest rounded-lg appearance-none cursor-pointer accent-primary border border-outline-variant/30"
        />
        <div className="flex justify-between mt-2 text-[10px] font-mono text-on-surface-variant uppercase opacity-60">
          <span>Maintenance (0)</span>
          <span>Max Possible ({maxPossible.toLocaleString()})</span>
        </div>
      </div>
    </div>
  );
};

const HeadcountSlider = ({ 
  value, 
  required, 
  onChange, 
  disabled 
}: { 
  value: number, 
  required: number, 
  onChange: (v: number) => void,
  disabled: boolean
}) => {
  const maxVal = required > 0 ? required * 2 : 100;
  const minVal = 0;
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-end">
        <div className="flex items-center space-x-1">
            <label className="text-xs font-mono text-on-surface-variant uppercase tracking-widest">Global Workforce Deployment</label>
            <div className="group relative"><FiInfo size={10} className="text-on-surface-variant" /><Tooltip text="Assign your active workforce to maintenance and production. Understaffing will reduce effective throughput proportionately." /></div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-display text-on-surface">{value} <span className="text-xs text-on-surface-variant uppercase font-mono opacity-80">Staff</span></div>
          <div className="text-[10px] font-mono text-on-surface-variant uppercase tracking-widest">
            Optimal Required: <span className="text-primary font-bold">{required}</span>
          </div>
        </div>
      </div>
      <div className="relative pt-6">
        <div 
          className="absolute -top-1 w-1 h-8 bg-primary z-10 border-x border-surface"
          style={{ left: `${(required / maxVal) * 100}%` }}
        >
          <div className="absolute top-[-16px] left-[-30px] w-15 text-center text-[9px] font-bold text-primary uppercase tracking-tighter">EQUILIBRIUM</div>
        </div>

        <input 
          type="range"
          min={minVal}
          max={maxVal}
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value))}
          disabled={disabled}
          className="w-full h-2 bg-surface-highest rounded-lg appearance-none cursor-pointer accent-primary border border-outline-variant/30"
        />
        <div className="flex justify-between mt-2 text-[10px] font-mono text-on-surface-variant uppercase opacity-60">
          <span>0 (Min)</span>
          <span className="text-center font-bold text-primary opacity-100">Optimal ({required})</span>
          <span>Max ({maxVal})</span>
        </div>
      </div>
    </div>
  );
};

const ContextualStats = ({ 
  title, 
  stock,
  maintCost, 
  rndCost, 
  buyCost 
}: { 
  title: string, 
  stock: number[] | undefined,
  maintCost: number, 
  rndCost: number, 
  buyCost: number 
}) => (
  <div className="bg-surface-low border border-outline-variant overflow-hidden">
    <div className="bg-surface-highest/50 px-4 py-2 border-b border-outline-variant flex justify-between items-center">
      <span className="text-[10px] font-mono text-primary uppercase tracking-[0.2em] font-bold">{title} Status</span>
      <FiBarChart2 className="text-primary" size={14} />
    </div>
    <div className="p-4 flex flex-col space-y-6">
      <div className="min-h-[100px] flex flex-col">
        <StockHistogram stock={stock} label="Output Buffer Quality" />
      </div>
      <div className="pt-4 border-t border-outline-variant/30">
        <div className="text-[10px] font-mono text-on-surface-variant uppercase mb-2">Cycle Costing Context</div>
        <div className="space-y-1 text-[11px] font-mono text-on-surface opacity-80">
          <div className="flex justify-between"><span>Maintenance:</span> <span>${maintCost.toLocaleString()}</span></div>
          {rndCost > 0 && <div className="flex justify-between text-tertiary font-bold"><span>Next R&D:</span> <span>${rndCost.toLocaleString()}</span></div>}
          {buyCost > 0 && <div className="flex justify-between text-primary font-bold"><span>Hardware P:</span> <span>${buyCost.toLocaleString()}</span></div>}
        </div>
      </div>
    </div>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────────
// Main Page
// ─────────────────────────────────────────────────────────────────────────────

export const Production = () => {
  const { phase, cycleNumber } = useGameStore();
  const { addToast } = useNotificationStore();
  const { components, skillLevel, morale, automationLevel, fetchInventory, funds } = useInventoryStore();

  const {
    componentDecisions, wageLevel, targetHeadcount, upgradeAutomation,
    selectedComponent, setComponent, setMaintenance, setUnitsToProduce, setRndInvest, clearRndInvest,
    setWageLevel, setHeadcount, setAutomation, setBuyMachine, fetchExistingDecisions, submitDecisions
  } = useProductionStore();

  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchExistingDecisions();
    fetchInventory();
  }, [fetchExistingDecisions, fetchInventory]);

  const isProductionOpen = phase === 'production_open';
  const currentComp = componentDecisions[selectedComponent];
  const factoryCompData = useMemo(() => components.find(c => c.component === selectedComponent), [components, selectedComponent]);

  const liveStats = useMemo(() => {
    let totalMaint = 0;
    let totalRnd = 0;
    let totalBuy = 0;

    (Object.entries(componentDecisions) as [ComponentType, any][]).forEach(([comp, dec]) => {
      totalMaint += MAINTENANCE_COSTS[dec.maintenance as keyof typeof MAINTENANCE_COSTS] * (components.find(c => c.component === comp)?.machine_count || 0);
      if (dec.rnd_invest) totalRnd += dec.rnd_invest.levels * RND_COST_PER_LEVEL;
      if (dec.buy_machine) totalBuy += MACHINE_TIERS[dec.buy_machine.tier as keyof typeof MACHINE_TIERS].buy;
    });

    const wageCost = (targetHeadcount || 0) * WAGE_COSTS[wageLevel as keyof typeof WAGE_COSTS];
    const automationUpgradeCost = upgradeAutomation !== automationLevel ? AUTOMATION_UPGRADE_COST[upgradeAutomation as keyof typeof AUTOMATION_UPGRADE_COST] : 0;
    const totalOutflow = totalMaint + totalRnd + totalBuy + wageCost + automationUpgradeCost;

    let totalRequiredLabour = 0;
    (Object.entries(componentDecisions) as [ComponentType, any][]).forEach(([comp, dec]) => {
      const existingMachines = components.find(c => c.component === comp)?.machines || [];
      const labourMult = AUTOMATION_LABOUR_MULT[upgradeAutomation as keyof typeof AUTOMATION_LABOUR_MULT] || 1.0;
      existingMachines.forEach(m => {
        const cfg = MACHINE_TIERS[m.tier as keyof typeof MACHINE_TIERS];
        totalRequiredLabour += Math.floor(cfg.labour * labourMult);
      });
      if (dec.buy_machine) {
        const cfg = MACHINE_TIERS[dec.buy_machine.tier as keyof typeof MACHINE_TIERS];
        totalRequiredLabour += Math.floor(cfg.labour * labourMult);
      }
    });

    const labourGap = totalRequiredLabour - targetHeadcount;
    const understaffingPct = totalRequiredLabour > 0 ? Math.max(0, (totalRequiredLabour - targetHeadcount) / totalRequiredLabour) * 100 : 0;
    const labourFactor = totalRequiredLabour > 0 ? Math.min(1.0, targetHeadcount / totalRequiredLabour) : 1.0;
    const projectedMoraleDelta = calculateMoraleDelta(wageLevel, understaffingPct);
    const projectedMorale = Math.max(0, Math.min(100, (morale || 0) + projectedMoraleDelta));

    const activeMachines = factoryCompData?.machines || [];
    const simulatedMachines = [...activeMachines];
    if (currentComp.buy_machine) {
      const buyTier = currentComp.buy_machine.tier;
      simulatedMachines.push({
        id: -1, tier: buyTier, condition: 100, source: 'Purchased', is_active: true,
        throughput: MACHINE_TIERS[buyTier].throughput, base_grade: MACHINE_TIERS[buyTier].grade,
      });
    }

    const rnd_q = (factoryCompData?.rnd_quality || 0);
    const rnd_c = (factoryCompData?.rnd_consistency || 0);
    const projSigma = calculateProjectedSigma(upgradeAutomation, skillLevel || 0, rnd_c);
    const projMean = calculateEffectiveGrade(simulatedMachines, rnd_q);
    const tp_base = simulatedMachines.reduce((s, m) => s + (MACHINE_TIERS[m.tier as keyof typeof MACHINE_TIERS]?.throughput || 0), 0);
    const projThroughput = tp_base * labourFactor;

    const selectedCompMaint = MAINTENANCE_COSTS[currentComp.maintenance as keyof typeof MAINTENANCE_COSTS] * (factoryCompData?.machine_count || 0);
    const selectedCompRnd = currentComp.rnd_invest ? currentComp.rnd_invest.levels * RND_COST_PER_LEVEL : 0;
    const selectedCompBuy = currentComp.buy_machine ? MACHINE_TIERS[currentComp.buy_machine.tier as keyof typeof MACHINE_TIERS].buy : 0;

    return {
      totalMaint, totalRnd, totalBuy, wageCost, totalOutflow, automationUpgradeCost,
      totalRequiredLabour, labourGap, understaffingPct, labourFactor,
      projectedMorale, projectedMoraleDelta,
      projSigma, projMean, projThroughput,
      stockLimit: (factoryCompData?.raw_stock_total || 0),
      selectedCompMaint, selectedCompRnd, selectedCompBuy,
      remainingFunds: (funds || 0) - totalOutflow,
      fundUsagePct: (funds || 0) > 0 ? (totalOutflow / funds) * 100 : 100
    };
  }, [componentDecisions, components, targetHeadcount, wageLevel, upgradeAutomation, automationLevel, morale, skillLevel, factoryCompData, currentComp, funds]);

  const handleSubmit = async () => {
    if (!window.confirm('Confirm all production decisions?')) return;
    setIsSubmitting(true);
    try {
      await submitDecisions();
      addToast('Production decisions transmitted to factory floor.', 'success');
    } catch (err: any) {
      addToast(err?.message || 'Transmission failure.', 'error');
    } finally { setIsSubmitting(false); }
  };

  const fundUsagePct = liveStats.fundUsagePct;
  let progressColor = "bg-[#3b82f6]"; // Blue for < 25%
  if (fundUsagePct >= 25 && fundUsagePct < 50) progressColor = "bg-[#10b981]"; // Green
  else if (fundUsagePct >= 50 && fundUsagePct < 75) progressColor = "bg-[#eab308]"; // Yellow
  else if (fundUsagePct >= 75) progressColor = "bg-error"; // Red
  const isOverflowing = liveStats.remainingFunds < 0;

  return (
    <div className="flex flex-col h-full space-y-4">
      <ComponentTabs selected={selectedComponent} onSelect={setComponent} />
      
      <div className="flex justify-between items-end flex-shrink-0">
        <div>
          <h1 className="font-display text-4xl uppercase tracking-tighter">DECISION COCKPIT</h1>
          <div className="text-on-surface-variant font-mono text-sm mt-1 tracking-widest opacity-80 flex items-center space-x-2">
            <span>Cycle {cycleNumber} — Production Operations & Labour Strategy</span>
          </div>
        </div>
        <div className="flex items-center space-x-3 bg-primary/10 border border-primary/20 px-4 py-2 rounded-full group relative cursor-help">
          <div className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(var(--primary-rgb),0.8)]" />
          <span className="text-xs font-mono text-primary uppercase tracking-widest font-bold">Feedback Loop Operative</span>
          <Tooltip text="Real-time projection engine is active. Values update dynamically as you tweak decisions." />
        </div>
      </div>

      <div className="flex flex-1 space-x-6 min-h-0 overflow-hidden">
        {/* LEFT PANEL: INPUTS */}
        <div className="w-[50%] flex flex-col space-y-4 overflow-y-auto pr-2 custom-scrollbar">
          <div className="bg-surface-low border border-outline-variant p-6 space-y-7">
            <h2 className="text-sm font-mono text-primary uppercase tracking-[0.25em] flex items-center space-x-2 border-b border-outline-variant pb-4">
              <FiSettings size={16} /> <span>{selectedComponent.replace('_', ' ')} Directives</span>
            </h2>

            <ProductionDropdown 
              label="Fleet Maintenance Protocol"
              value={currentComp.maintenance}
              disabled={!isProductionOpen}
              onChange={(v) => setMaintenance(selectedComponent, v)}
              tooltip="Select the intensity level for proactive machine care. Higher levels reduce condition decay but increase operational costs."
              options={[
                { value: 'none', label: 'Reactive (Zero)', info: 'Degrade at 1.0x. No preventative care.', cost: 0 },
                { value: 'basic', label: 'Standard (Low)', info: 'Degrade at 0.5x. Basic preventative routines.', cost: MAINTENANCE_COSTS.basic },
                { value: 'full', label: 'Proactive (High)', info: 'Degrade at 0.2x. Deep diagnostic sensor care.', cost: MAINTENANCE_COSTS.full },
                { value: 'overhaul', label: 'Restorative (Overhaul)', info: 'Recovery up to +20 Condition units. Physical restoration.', cost: MAINTENANCE_COSTS.overhaul }
              ]}
            />

            <BottleneckSlider 
              label="Production Target Allocation"
              value={currentComp.units_to_produce}
              throughputLimit={factoryCompData?.total_throughput || 0}
              stockLimit={liveStats.stockLimit}
              onChange={(v) => setUnitsToProduce(selectedComponent, v)}
              disabled={!isProductionOpen}
            />

            <div className="space-y-6 pt-2">
              <h3 className="text-xs font-mono text-tertiary uppercase tracking-widest flex items-center space-x-2">
                <FiZap size={14} /> <span>Hardware Innovation Tracks</span>
              </h3>
              <DiscreteStepBar 
                label="Mean Output Grade"
                currentLevel={factoryCompData?.rnd_quality || 0}
                projectedLevel={currentComp.rnd_invest?.focus === 'quality' ? (factoryCompData?.rnd_quality || 0) + 1 : (factoryCompData?.rnd_quality || 0)}
                maxLevels={5} cost={RND_COST_PER_LEVEL}
                isUpgradeLocked={!!factoryCompData?.rnd_in_progress?.some(p => p.focus === 'quality' || p.focus === 'mean')}
                onAdd={() => {
                  if (currentComp.rnd_invest?.focus === 'quality') clearRndInvest(selectedComponent);
                  else setRndInvest(selectedComponent, 'quality', 1);
                }}
                disabled={!isProductionOpen}
                tooltip="Increases the target baseline quality for all units produced in this slot."
                info="Structural reinforcement & surface finish optimization."
              />
              <DiscreteStepBar 
                label="Process Consistency"
                currentLevel={factoryCompData?.rnd_consistency || 0}
                projectedLevel={currentComp.rnd_invest?.focus === 'consistency' ? (factoryCompData?.rnd_consistency || 0) + 1 : (factoryCompData?.rnd_consistency || 0)}
                maxLevels={5} cost={RND_COST_PER_LEVEL}
                isUpgradeLocked={!!factoryCompData?.rnd_in_progress?.some(p => p.focus === 'consistency')}
                onAdd={() => {
                  if (currentComp.rnd_invest?.focus === 'consistency') clearRndInvest(selectedComponent);
                  else setRndInvest(selectedComponent, 'consistency', 1);
                }}
                disabled={!isProductionOpen}
                tooltip="Reduces output variance (Sigma), results in more predictable quality tiers."
                info="Calibrated sensor loops & predictive timing."
              />
              <DiscreteStepBar 
                label="Raw Material Yield"
                currentLevel={factoryCompData?.rnd_yield || 0}
                projectedLevel={currentComp.rnd_invest?.focus === 'yield' ? (factoryCompData?.rnd_yield || 0) + 1 : (factoryCompData?.rnd_yield || 0)}
                maxLevels={5} cost={RND_COST_PER_LEVEL}
                isUpgradeLocked={!!factoryCompData?.rnd_in_progress?.some(p => p.focus === 'yield')}
                onAdd={() => {
                  if (currentComp.rnd_invest?.focus === 'yield') clearRndInvest(selectedComponent);
                  else setRndInvest(selectedComponent, 'yield', 1);
                }}
                disabled={!isProductionOpen}
                tooltip="Optimizes material consumption, effectively increasing units per RM batch."
                info="Scrap reduction & nesting algorithm upgrades."
              />
            </div>
          </div>

          <div className="bg-surface-low border border-outline-variant p-6 space-y-9">
            <h2 className="text-sm font-mono text-primary uppercase tracking-[0.25em] flex items-center space-x-2 border-b border-outline-variant pb-4">
              <FiUsers size={16} /> <span>Enterprise Operations</span>
            </h2>
            <ProductionDropdown 
              label="Compensation Tier Selection"
              value={wageLevel}
              disabled={!isProductionOpen}
              onChange={setWageLevel}
              tooltip="Governs base morale trends. Austerity saves funds but risks strikes and poaching."
              options={[
                { value: 'below_market', label: 'Operational Austerity', info: 'Lowers morale, reduces costs significantly.', cost: WAGE_COSTS.below_market },
                { value: 'market', label: 'Stable Market Rate', info: 'Maintains equilibrium morale.', cost: WAGE_COSTS.market },
                { value: 'above_market', label: 'Premium Incentive', info: 'Boosts morale and productivity metrics.', cost: WAGE_COSTS.above_market }
              ]}
            />
            <HeadcountSlider 
              value={targetHeadcount}
              required={liveStats.totalRequiredLabour}
              onChange={setHeadcount}
              disabled={!isProductionOpen}
            />
            <DiscreteStepBar 
              label="Facility Automation Tier"
              currentLevel={automationLevel === 'manual' ? 0 : automationLevel === 'semi_auto' ? 1 : 2}
              projectedLevel={
                upgradeAutomation === 'manual' ? 0 : (upgradeAutomation === 'semi_auto' ? 1 : 2)
              }
              maxLevels={2}
              isUpgradeLocked={false}
              cost={AUTOMATION_UPGRADE_COST[automationLevel === 'manual' ? 'semi_auto' : (automationLevel === 'semi_auto' ? 'full_auto' : 'full_auto')]}
              onAdd={() => {
                const levels = (['manual', 'semi_auto', 'full_auto'] as const);
                const currentIdx = levels.indexOf(automationLevel as any);
                const projectedIdx = levels.indexOf(upgradeAutomation as any);
                if (projectedIdx > currentIdx) setAutomation(automationLevel as any);
                else if (currentIdx < 2) setAutomation(levels[currentIdx + 1]);
              }}
              disabled={!isProductionOpen}
              tooltip="Decreases total human workforce requirements and lowers manufacture variance."
              info="Digital twins & cobot integration."
            />
          </div>
        </div>

        {/* RIGHT PANEL: COCKPIT PREVIEW */}
        <div className="flex-1 flex flex-col space-y-4 min-w-0">
          <div className="grid grid-cols-2 gap-4">
            <MetricBox label="Projected Morale" value={`${liveStats.projectedMorale.toFixed(1)}%`} subvalue={`${liveStats.projectedMoraleDelta >= 0 ? '+' : ''}${liveStats.projectedMoraleDelta.toFixed(1)} delta/cycle`} icon={FiTrendingUp} color={liveStats.projectedMoraleDelta > 0 ? 'text-primary' : liveStats.projectedMoraleDelta < 0 ? 'text-error' : 'text-on-surface'} tooltip="Projected team sentiment after cycle resolution. Morale influences skill gain and strike risk." />
            <MetricBox label="Labour Status" value={liveStats.labourGap <= 0 ? 'OPTIMAL' : `${liveStats.labourGap} DEFICIT`} subvalue={liveStats.labourGap <= 0 ? '100% Productivity' : `${Math.round(liveStats.labourFactor * 100)}% Productivity`} icon={FiUsers} color={liveStats.labourGap > 0 ? 'text-error' : 'text-primary'} tooltip="Workforce efficiency based on available staff vs required labour for active machines." />
            <MetricBox label="Output Quality" value={`${Math.round(liveStats.projMean)} GR`} subvalue={`±${liveStats.projSigma.toFixed(1)} Variance`} icon={FiCpu} tooltip="Expected weighted mean grade across all active machines, including R&D bonuses." />
            <MetricBox label="Global Outflow" value={`$${liveStats.totalOutflow.toLocaleString()}`} subvalue={`Includes $${liveStats.totalBuy.toLocaleString()} CapEx`} icon={FiPlusCircle} color="text-tertiary" tooltip="Total projected expenditure for this cycle across all components and workforce." />
          </div>

          <div className="flex flex-col flex-1 bg-surface-low border border-outline-variant overflow-hidden">
            <div className="bg-surface-highest/50 px-6 py-4 border-b border-outline-variant flex justify-between items-center flex-shrink-0">
              <h2 className="text-sm font-mono text-on-surface-variant uppercase tracking-[0.25em] flex items-center space-x-2">
                <FiTool size={16} /> <span>Active System Health</span>
              </h2>
            </div>
            
            <div className="flex-1 overflow-y-auto space-y-4 p-6 custom-scrollbar">
              {factoryCompData?.machines?.map((mac, idx) => {
                const projected = calculateProjectedCondition(mac.condition, currentComp.maintenance, mac.tier);
                return (
                  <div key={idx} className="bg-surface/50 border border-outline-variant/30 p-4 space-y-4 shadow-sm group relative cursor-help">
                    <div className="flex justify-between items-center text-xs font-mono font-bold">
                      <span className="uppercase text-primary">{mac.tier} Grade {mac.source}</span>
                      <span className="text-on-surface-variant bg-surface-highest px-2 py-0.5 rounded">TP: {MACHINE_TIERS[mac.tier as keyof typeof MACHINE_TIERS]?.throughput}</span>
                    </div>
                    <HealthBar current={mac.condition} projected={projected} label="Hardware Health Status" />
                    <Tooltip title={`Machine #${mac.id || idx+1}`} text={`Throughput: ${MACHINE_TIERS[mac.tier as keyof typeof MACHINE_TIERS]?.throughput} units/cycle. Base Grade: ${MACHINE_TIERS[mac.tier as keyof typeof MACHINE_TIERS]?.grade}. Current condition affects output quality.`} />
                  </div>
                );
              })}

              <div className="bg-surface/30 border border-outline-variant/30 border-dashed p-6 text-center space-y-5 rounded-lg">
                {currentComp.buy_machine ? (
                  <div className="space-y-4 animate-in zoom-in-95">
                    <div className="text-xs font-mono text-tertiary uppercase tracking-widest font-bold">Pending Acquisition Selected</div>
                    <div className="grid grid-cols-2 gap-3">
                      {(Object.entries(MACHINE_TIERS) as [string, any][]).map(([tier, cfg]) => (
                        <button key={tier} onClick={() => setBuyMachine(selectedComponent, tier as any)} className={`p-3 border text-left transition-all relative ${currentComp.buy_machine?.tier === tier ? 'bg-tertiary/10 border-tertiary shadow-inner' : 'bg-surface border-outline-variant hover:border-on-surface-variant'}`}>
                          <div className="flex justify-between items-center mb-1">
                            <span className={`text-xs font-bold uppercase ${currentComp.buy_machine?.tier === tier ? 'text-tertiary' : 'text-on-surface'}`}>{tier}</span>
                          </div>
                          <div className="text-[10px] font-mono text-on-surface-variant uppercase opacity-80">Cost: ${(cfg.buy/1000).toFixed(0)}k · TP: {cfg.throughput}</div>
                          {currentComp.buy_machine?.tier === tier && <div className="absolute top-1 right-1 text-tertiary font-bold animate-pulse text-[8px]">ACTIVE</div>}
                        </button>
                      ))}
                    </div>
                    <button onClick={() => setBuyMachine(selectedComponent, null)} className="text-[11px] font-mono text-error uppercase tracking-widest flex items-center justify-center space-x-2 mx-auto hover:bg-error/5 py-1 px-4 rounded transition-colors font-bold">
                      <FiX size={14} /> <span>Cancel Acquisition</span>
                    </button>
                  </div>
                ) : (
                  <div className="py-2">
                    <div className="text-xs font-mono text-on-surface-variant uppercase tracking-[0.25em] mb-4">Capacity Management</div>
                    <button onClick={() => setBuyMachine(selectedComponent, 'basic')} className="group flex flex-col items-center justify-center space-y-3 mx-auto">
                      <div className="p-5 rounded-full bg-surface-highest border border-outline-variant text-on-surface-variant group-hover:text-primary group-hover:border-primary transition-all group-hover:shadow-[0_0_25px_rgba(var(--primary-rgb),0.3)]">
                        <FiPlusSquare size={36} />
                      </div>
                      <span className="text-xs font-mono uppercase tracking-[0.2em] text-on-surface-variant group-hover:text-primary font-bold">Procure Extra Hardware</span>
                      <Tooltip text="Purchase additional machines to increase production capacity. New machines arrive immediately at full condition." />
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Contextual Status Strip */}
            <div className="p-4 bg-surface-highest/20 border-t border-outline-variant/30 space-y-4">
                <ContextualStats 
                    title={selectedComponent.replace('_', ' ')}
                    stock={factoryCompData?.finished_stock}
                    maintCost={liveStats.selectedCompMaint}
                    rndCost={liveStats.selectedCompRnd}
                    buyCost={liveStats.selectedCompBuy}
                />
            </div>
          </div>
        </div>
      </div>

      {/* Global Fund Summary & Decision Commit */}
      <div className="bg-surface-container border border-outline-variant p-6 flex flex-col space-y-4 flex-shrink-0">
        <div className="flex justify-between items-center">
            <div className="flex space-x-12">
                <div className="flex flex-col group relative cursor-help">
                    <span className="text-xs text-on-surface-variant uppercase tracking-widest font-mono flex items-center space-x-1">
                        <span>Maintenance</span>
                        <FiInfo size={10} />
                    </span>
                    <span className="text-lg font-mono text-on-surface font-bold">${liveStats.totalMaint.toLocaleString()}</span>
                    <Tooltip text="Cumulative maintenance cost for all components across all machines." />
                </div>
                <div className="flex flex-col group relative cursor-help">
                    <span className="text-xs text-on-surface-variant uppercase tracking-widest font-mono flex items-center space-x-1">
                        <span>R&D / CapEx</span>
                        <FiInfo size={10} />
                    </span>
                    <span className="text-lg font-mono text-on-surface font-bold text-tertiary">${(liveStats.totalRnd + liveStats.totalBuy).toLocaleString()}</span>
                    <Tooltip text="Total capital expenditure for R&D levels and new machine purchases." />
                </div>
                <div className="flex flex-col group relative cursor-help">
                    <span className="text-xs text-on-surface-variant uppercase tracking-widest font-mono flex items-center space-x-1">
                        <span>Labour Net</span>
                        <FiInfo size={10} />
                    </span>
                    <span className="text-lg font-mono text-on-surface font-bold">${(liveStats.wageCost + liveStats.automationUpgradeCost).toLocaleString()}</span>
                    <Tooltip text="Personnel costs including wages and automation integration fees." />
                </div>
            </div>

            <div className="flex items-center space-x-10">
                <div className="text-right">
                    <div className="text-xs text-on-surface-variant uppercase tracking-[0.2em] font-bold">CYCLE CASH OUTFLOW</div>
                    <div className={`text-4xl font-display ${isOverflowing ? 'text-error animate-pulse' : 'text-primary'}`}>${liveStats.totalOutflow.toLocaleString()}</div>
                </div>
                <div className="w-72">
                    <SendDecisionsButton onClick={handleSubmit} disabled={!isProductionOpen} loading={isSubmitting} />
                </div>
            </div>
        </div>

        {/* Global Fund Utilization Bar */}
        <div className="space-y-2 pt-2 border-t border-outline-variant/30">
            <div className="flex justify-between items-center text-[11px] font-mono uppercase tracking-widest">
                <span className="flex items-center space-x-2">
                    <FiDollarSign className={isOverflowing ? 'text-error' : 'text-primary'} />
                    <span className="text-on-surface-variant">Global Fund Utilisation ({fundUsagePct.toFixed(1)}%)</span>
                </span>
                <span className={isOverflowing ? 'text-error font-bold' : 'text-primary font-bold'}>
                    {isOverflowing ? `DEFICIT: $${Math.abs(liveStats.remainingFunds).toLocaleString()}` : `SURPLUS: $${liveStats.remainingFunds.toLocaleString()}`}
                </span>
            </div>
            
            <div className="w-full bg-surface h-3.5 border border-outline-variant relative overflow-hidden rounded-sm group">
                <div className={`h-full ${progressColor} transition-all duration-500 ease-out`} style={{ width: `${Math.min(fundUsagePct, 100)}%` }} />
                {isOverflowing && (
                  <div className="absolute inset-0 bg-error/40 animate-pulse" style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.2) 10px, rgba(255,255,255,0.2) 20px)' }}></div>
                )}
                <Tooltip title="Liquidity Meter" text={`Your current liquid funds: $${(funds || 0).toLocaleString()}. Projected surplus/deficit after this cycle takes all costs into account.`} />
            </div>

            {isOverflowing && (
              <div className="flex justify-between items-center bg-error/10 border-l-4 border-error p-3 rounded-r animate-in slide-in-from-left-2">
                <div className="flex items-center space-x-3">
                  <FiAlertCircle className="text-error" size={18} />
                  <div>
                    <span className="text-error font-bold text-[10px] uppercase block tracking-widest">CASH CRUNCH DETECTED</span>
                    <span className="text-on-surface text-[10px] opacity-80 font-mono">Expenditure exceeds project reserves. Emergency loans will be triggered upon resolution.</span>
                  </div>
                </div>
                <div className="text-error font-mono font-bold text-xs">-${Math.abs(liveStats.remainingFunds).toLocaleString()}</div>
              </div>
            )}
        </div>
      </div>
    </div>
  );
};
