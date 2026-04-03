import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useGameStore } from '../store';
import { useEffect } from 'react';
import { MdFactory, MdCampaign, MdPrecisionManufacturing, MdLogout } from 'react-icons/md';

export const SharedLayout = () => {
  const { isLoggedIn, phase, logout, pollStatus } = useGameStore();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isLoggedIn) {
      navigate('/login');
      return;
    }

    // Start polling status
    pollStatus();
    const interval = setInterval(pollStatus, 5000);
    return () => clearInterval(interval);
  }, [isLoggedIn, navigate, pollStatus]);

  if (!isLoggedIn) return null;

  const navItems = [
    { path: '/', label: 'HOME' },
    { path: '/market', label: 'MARKET' },
    { path: '/inventory', label: 'INVENTORY' },
    { path: '/event', label: 'EVENT' },
  ];

  const sideItems = [
    { id: 'raw_materials', label: 'RAW MATERIALS', icon: <MdFactory /> },
    { id: 'marketing', label: 'MARKETING', icon: <MdCampaign /> },
    { id: 'automation', label: 'AUTOMATION LEVEL', icon: <MdPrecisionManufacturing /> },
  ];

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
        <div className="flex items-center space-x-6">
          <div className="text-on-surface-variant font-mono text-xs">
            PHASE: <span className="text-primary font-bold ml-2 uppercase">{phase.replace('_', ' ')}</span>
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

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-surface-low border-r border-outline-variant flex flex-col py-6 space-y-2">
          {sideItems.map((item, idx) => (
            <button
              key={item.id}
              className={`flex items-center space-x-4 px-6 py-4 w-full transition-colors 
                ${idx === 0 ? 'bg-surface-highest text-primary border-l-2 border-primary' : 'text-on-surface-variant hover:bg-surface-highest/50'}
              `}
            >
              <div className="text-xl">{item.icon}</div>
              <span className="font-display text-xs tracking-widest uppercase text-left">{item.label}</span>
            </button>
          ))}
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-8 relative">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
