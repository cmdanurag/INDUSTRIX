import { NavLink } from "react-router-dom";
import { useGameStore } from "../store/useGameStore";

const navItems = [
  { to: "/", label: "HOME" },
  { to: "/market", label: "MARKET" },
  { to: "/inventory", label: "INVENTORY" },
  { to: "/event", label: "EVENT" },
];

export const Layout = ({ children }: { children: React.ReactNode }) => {
  const { logout, phase, cycleNumber, gameName } = useGameStore();
  return (
    <div className="min-h-screen bg-surface text-on-surface">
      <header className="flex items-center justify-between bg-surface-low px-6 py-3">
        <div className="flex gap-6 text-sm tracking-wide">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `uppercase ${isActive ? "text-primary" : "text-on-surface-variant"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
        <button className="uppercase text-on-surface-variant" onClick={logout} type="button">
          LOGOUT
        </button>
      </header>
      <div className="mx-auto max-w-7xl p-4">
        <div className="mb-4 flex gap-4 text-xs text-on-surface-variant uppercase">
          <span>{gameName || "INDUSTRIX"}</span>
          <span>Cycle {cycleNumber}</span>
          <span>Phase: {phase}</span>
        </div>
        {children}
      </div>
    </div>
  );
};
