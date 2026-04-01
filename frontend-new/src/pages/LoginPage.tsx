import { useState } from "react";
import { useGameStore } from "../store/useGameStore";

export const LoginPage = () => {
  const [teamId, setTeamId] = useState("1");
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const { setCredentials, lastError } = useGameStore();

  return (
    <div className="mx-auto mt-24 max-w-md bg-surface-container p-6">
      <h1 className="mb-4 text-xl uppercase">Team Login</h1>
      <label className="mb-1 block text-xs uppercase text-on-surface-variant">Team ID</label>
      <input
        className="mb-3 w-full bg-surface-high p-2"
        type="number"
        value={teamId}
        onChange={(e) => setTeamId(e.target.value)}
      />
      <label className="mb-1 block text-xs uppercase text-on-surface-variant">PIN</label>
      <input
        className="mb-4 w-full bg-surface-high p-2"
        type="password"
        value={pin}
        onChange={(e) => setPin(e.target.value)}
      />
      <button
        type="button"
        disabled={loading}
        className="w-full bg-gradient-to-r from-primary to-primary-container p-2 uppercase text-black disabled:opacity-50"
        onClick={async () => {
          setLoading(true);
          try {
            await setCredentials(Number(teamId), pin);
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Logging in..." : "Login"}
      </button>
      {lastError && <p className="mt-3 text-sm text-error">{lastError}</p>}
    </div>
  );
};
