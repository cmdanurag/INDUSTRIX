import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useGameStore } from '../store';
import { useEffect, useMemo, useRef, useState } from 'react';
import { MdFactory, MdCampaign, MdPrecisionManufacturing, MdLogout } from 'react-icons/md';
import { useInventoryStore } from '../store';
import { useNotificationStore } from '../store/useNotificationStore';

export const SharedLayout = () => {
  const { isLoggedIn, phase, cycleNumber, lastSyncTs, connectionOk, logout, pollStatus } = useGameStore();
  const { funds, brandScore, automationLevel, workforceSize, morale, skillLevel, fetchInventory } = useInventoryStore();
  const { toasts, addToast, removeToast } = useNotificationStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [lastPhase, setLastPhase] = useState<string | null>(null);
  const intervalRef = useRef<number | null>(null);
  const [pollIntervalMs, setPollIntervalMs] = useState<number>(5000);
  const [lastPhaseChangeAt, setLastPhaseChangeAt] = useState<number>(Date.now());
  const [nowTs, setNowTs] = useState<number>(Date.now());
  const negativeFundsToastRef = useRef<boolean>(false);
  const [expandedSideItem, setExpandedSideItem] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }

    // Start polling status with dynamic backoff
    const startPolling = () => {
      if (phase === 'game_over') return;
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
      }
      pollStatus();
      intervalRef.current = window.setInterval(() => {
        pollStatus();
      }, pollIntervalMs) as unknown as number;
    };

    startPolling();
    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isLoggedIn, navigate, pollStatus, pollIntervalMs, phase]);

  useEffect(() => {
    const timer = window.setInterval(() => setNowTs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  // Backoff after 2 minutes without phase change; reset on change
  useEffect(() => {
    if (lastPhase === null) {
      setLastPhase(phase);
      setLastPhaseChangeAt(Date.now());
      return;
    }
    if (phase !== lastPhase) {
      setLastPhase(phase);
      setLastPhaseChangeAt(Date.now());
      // Reset to 5s polling immediately
      setPollIntervalMs(5000);
      if (lastPhase) {
        addToast(`Phase changed: ${phase.replace('_', ' ')} is now open`, 'info');
      }
    } else {
      const elapsed = Date.now() - lastPhaseChangeAt;
      if (elapsed > 120000 && pollIntervalMs !== 15000) {
        setPollIntervalMs(15000);
      }
    }
  }, [phase, lastPhase, lastPhaseChangeAt, pollIntervalMs]);

  // Keep global funds fresh periodically (no heavy polling)
  useEffect(() => {
    if (isLoggedIn) {
      fetchInventory().catch(() => {});
    }
  }, [isLoggedIn, fetchInventory, phase]);

  useEffect(() => {
    if (funds < 0 && !negativeFundsToastRef.current) {
      addToast('Warning: funds are negative', 'warning');
      negativeFundsToastRef.current = true;
    }
    if (funds >= 0) {
      negativeFundsToastRef.current = false;
    }
  }, [funds, addToast]);

  if (!isLoggedIn) return null;

  const navItems = [
    { path: '/', label: 'HOME' },
    { path: '/market', label: 'MARKET' },
    { path: '/inventory', label: 'INVENTORY' },
    { path: '/event', label: 'EVENT' },
  ];

  const sideItems = [
    { 
      id: 'factory', 
      label: 'FACTORY OVERVIEW', 
      icon: <MdFactory />,
      details: (
        <div className="space-y-2 mt-2 pl-10 text-xs font-mono text-on-surface-variant">
          <div className="flex justify-between"><span>Workforce:</span> <span className="text-on-surface">{workforceSize}</span></div>
          <div className="flex justify-between"><span>Skill Level:</span> <span className="text-on-surface">{skillLevel?.toFixed(1) || 0}</span></div>
          <div className="flex justify-between"><span>Morale:</span> <span className="text-on-surface">{morale?.toFixed(1) || 0}</span></div>
        </div>
      )
    },
    { 
      id: 'marketing', 
      label: 'MARKETING', 
      icon: <MdCampaign />,
      details: (
        <div className="space-y-2 mt-2 pl-10 text-xs font-mono text-on-surface-variant">
          <div className="flex justify-between"><span>Brand Score:</span> <span className="text-primary">{brandScore?.toFixed(1) || 0}</span></div>
        </div>
      )
    },
    { 
      id: 'automation', 
      label: 'AUTOMATION LEVEL', 
      icon: <MdPrecisionManufacturing />,
      details: (
        <div className="space-y-2 mt-2 pl-10 text-xs font-mono text-on-surface-variant">
          <div className="flex justify-between"><span>Current Tier:</span> <span className="text-on-surface capitalize">{automationLevel.replace('_', ' ')}</span></div>
        </div>
      )
    },
  ];

  const syncAgeSeconds = useMemo(() => {
    if (!lastSyncTs) return null;
    return Math.max(0, Math.floor((nowTs - lastSyncTs) / 1000));
  }, [lastSyncTs, nowTs]);

  return (
    <div className="flex flex-col min-h-screen bg-surface">
      {/* Top Navbar */}
      <nav className="flex justify-between items-center bg-surface-low px-6 py-4 border-b border-outline-variant">
        <div className="flex space-x-8">
          {navItems.map(item => (
            <button
              key={item.label}
              onClick={() => navigate(item.path)}
              className={`font-display text-sm tracking-widest transition-colors ${
                location.pathname === item.path ? 'text-primary' : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="flex items-center space-x-8">
          <div className="text-on-surface-variant font-mono text-xs flex items-center space-x-2">
            <span className="flex items-center space-x-2 uppercase tracking-wider font-bold">
              <span className="opacity-50">...</span>
              <span className="opacity-50">&gt;</span>
              <span className={phase === 'procurement_open' ? 'text-primary' : 'opacity-40 hover:opacity-80 transition-opacity'}>PROCUREMENT</span>
              <span className="opacity-50">&gt;</span>
              <span className={phase === 'production_open' ? 'text-primary' : 'opacity-40 hover:opacity-80 transition-opacity'}>PRODUCTION</span>
              <span className="opacity-50">&gt;</span>
              <span className={phase === 'sales_open' ? 'text-primary' : 'opacity-40 hover:opacity-80 transition-opacity'}>SALES</span>
              <span className="opacity-50">&gt;</span>
              <span className={phase === 'backroom' ? 'text-primary' : 'opacity-40 hover:opacity-80 transition-opacity'}>BACKROOM</span>
              <span className="opacity-50">&gt;</span>
              <span className="opacity-50">...</span>
            </span>
            <span className="ml-3 pl-3 border-l border-outline-variant">CYCLE <span className="text-on-surface ml-1">{cycleNumber || 0}</span></span>
          </div>
          <div className="text-on-surface font-mono text-xs">
            <span className={`${funds < 0 ? 'text-error' : 'text-on-surface'}`}>${funds.toLocaleString()}</span>
          </div>
          {/* Sync status indicator */}
          <div className="flex items-center space-x-2 font-mono text-xs">
            <span className={`inline-block w-2 h-2 rounded-full ${connectionOk ? (syncAgeSeconds !== null && syncAgeSeconds > 15 ? 'bg-tertiary' : 'bg-primary') : 'bg-error'}`} />
            <span className="text-on-surface-variant">
              Last synced {syncAgeSeconds ?? '—'}s ago
            </span>
          </div>
          <button
            onClick={logout}
            className="flex items-center space-x-2 text-on-surface-variant hover:text-error transition-colors"
          >
            <span className="font-display text-sm tracking-widest">LOGOUT</span>
            <MdLogout />
          </button>
        </div>
      </nav>

      {/* Notification bar placeholder (toast stack area) */}
      <div className="px-6 py-2 border-b border-outline-variant bg-surface-highest">
        <div id="toast-stack" className="space-y-2 text-sm font-mono">
          {toasts.slice(-3).map((t) => (
            <div
              key={t.id}
              className={`px-3 py-2 border flex items-center justify-between ${
                t.type === 'success'
                  ? 'border-primary text-primary'
                  : t.type === 'error'
                    ? 'border-error text-error'
                    : t.type === 'warning'
                      ? 'border-tertiary text-tertiary'
                      : 'border-outline-variant text-on-surface'
              }`}
            >
              <span>{t.message}</span>
              <button className="text-on-surface-variant hover:text-on-surface" onClick={() => removeToast(t.id)}>
                DISMISS
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-surface-low border-r border-outline-variant flex flex-col py-6 space-y-2">
          {sideItems.map((item) => {
            const isExpanded = expandedSideItem === item.id;
            return (
              <div key={item.id} className="flex flex-col">
                <button
                  onClick={() => setExpandedSideItem(isExpanded ? null : item.id)}
                  className={`flex items-center space-x-4 px-6 py-4 w-full transition-colors 
                    ${isExpanded ? 'bg-surface-highest text-primary border-l-2 border-primary' : 'text-on-surface-variant hover:bg-surface-highest/50 border-l-2 border-transparent'}
                  `}
                >
                  <div className="text-xl">{item.icon}</div>
                  <span className="font-display text-xs tracking-widest uppercase text-left">{item.label}</span>
                </button>
                {isExpanded && (
                  <div className="px-6 pb-4 bg-surface-highest border-l-2 border-primary">
                    {item.details}
                  </div>
                )}
              </div>
            );
          })}
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-8 relative">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
