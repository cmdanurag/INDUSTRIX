import React from 'react';

// Send Decisions Button
export const SendDecisionsButton = ({ 
  onClick, 
  disabled = false, 
  loading = false 
}: { 
  onClick: () => void; 
  disabled?: boolean;
  loading?: boolean;
}) => (
  <button
    onClick={onClick}
    disabled={disabled || loading}
    className={`w-full py-4 uppercase font-display font-bold tracking-wider 
      bg-gradient-to-br from-primary to-primary-container text-[#111417]
      transition-all duration-200
      ${disabled || loading ? 'opacity-30 cursor-not-allowed' : 'hover:opacity-90'}
    `}
  >
    {loading ? 'SENDING...' : 'SEND DECISIONS'}
  </button>
);

// Status Chip
export const StatusChip = ({ 
  label, 
  variant = 'active' 
}: { 
  label: string; 
  variant?: 'active' | 'warning' | 'error' | 'ghost'
}) => {
  const vMap = {
    active: 'bg-primary text-[#111417]',
    warning: 'bg-tertiary text-[#111417]',
    error: 'bg-error text-[#111417]',
    ghost: 'bg-surface-highest text-on-surface-variant'
  };
  return (
    <span className={`px-2 py-1 text-xs font-mono font-bold uppercase ${vMap[variant]}`}>
      {label}
    </span>
  );
};

// Metric Card
export const MetricCard = ({ 
  label, 
  value,
  subtext 
}: { 
  label: string; 
  value: string | number;
  subtext?: string;
}) => (
  <div className="bg-surface-container p-6 flex flex-col justify-between">
    <div className="text-on-surface-variant text-xs font-display uppercase tracking-widest mb-4">
      {label}
    </div>
    <div className="text-on-surface font-display text-4xl">
      {value}
    </div>
    {subtext && (
      <div className="text-on-surface-variant text-xs mt-2">
        {subtext}
      </div>
    )}
  </div>
);

// Warning Banner
export const WarningBanner = ({ message }: { message: string }) => (
  <div className="bg-tertiary/10 border-l-4 border-tertiary p-3 my-4">
    <p className="text-on-surface text-sm">{message}</p>
  </div>
);

// Component Tabs
import type { ComponentType } from '../types';
import { 
  MdArchitecture, 
  MdSettingsInputComponent, 
  MdFireExtinguisher,
  MdSensors,
  MdBatteryFull,
  MdRocket
} from 'react-icons/md';

const TABS: { id: ComponentType; label: string; icon: React.ReactNode }[] = [
  { id: 'airframe', label: 'AIRFRAME', icon: <MdArchitecture /> },
  { id: 'propulsion', label: 'PROPULSION', icon: <MdRocket /> },
  { id: 'avionics', label: 'AVIONICS', icon: <MdSettingsInputComponent /> },
  { id: 'fire_suppression', label: 'FIRE SUPPRESSION', icon: <MdFireExtinguisher /> },
  { id: 'sensing_safety', label: 'SENSING & SAFETY', icon: <MdSensors /> },
  { id: 'battery', label: 'BATTERY', icon: <MdBatteryFull /> },
];

export const ComponentTabs = ({ 
  selected, 
  onSelect 
}: { 
  selected: ComponentType; 
  onSelect: (c: ComponentType) => void;
}) => {
  return (
    <div className="flex bg-surface-low border-b border-outline-variant">
      {TABS.map(tab => {
        const isActive = selected === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onSelect(tab.id)}
            className={`flex-1 flex flex-col items-center justify-center py-4 px-2 
              hover:bg-surface-highest transition-colors
              ${isActive ? 'bg-surface-highest border-b-2 border-primary' : 'bg-transparent text-on-surface-variant'}
            `}
          >
            <div className={`text-xl mb-2 ${isActive ? 'text-primary' : 'text-on-surface-variant'}`}>
              {tab.icon}
            </div>
            <span className={`text-[10px] font-display uppercase tracking-widest ${isActive ? 'text-primary font-bold' : ''}`}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </div>
  );
};
