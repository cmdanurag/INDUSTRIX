import { useState, useEffect } from 'react';
import { useGameStore } from '../store';
import { useNavigate } from 'react-router-dom';

export const Login = () => {
  const [teamId, setTeamId] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, isLoggedIn } = useGameStore();
  const navigate = useNavigate();

  // Redirect if already logged in
  useEffect(() => {
    if (isLoggedIn) {
      navigate('/', { replace: true });
    }
  }, [isLoggedIn, navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(parseInt(teamId, 10), pin);
      // Navigation will happen automatically via useEffect when isLoggedIn becomes true
    } catch (err: any) {
        if (err.response) {
            if (err.response.status === 401 || err.response.status === 403)
                setError("Invalid credentials. Try again.");
            else setError("Something went wrong.");
        } else {
            setError("Server not reachable.");
        }
        setPin("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface relative overflow-hidden">
      {/* Abstract geometric background elements */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none grid grid-cols-12 gap-4 opacity-5">
        <div className="col-span-3 bg-on-surface h-full transform -skew-x-12 -translate-x-10" />
        <div className="col-span-1 border-r border-on-surface h-full" />
        <div className="col-span-2 col-start-8 bg-on-surface h-[200%] transform -skew-y-12 -translate-y-1/4" />
      </div>

      <div className="w-full max-w-md bg-surface-low border border-outline-variant p-8 relative z-10">
        <h1 className="font-display text-4xl mb-2 text-on-surface uppercase tracking-tighter">
          INDUSTRIX
        </h1>
        <p className="font-mono text-on-surface-variant text-sm mb-8">
          SYSTEM_ACCESS // AUTHENTICATION_REQUIRED
        </p>

        {error && (
          <div className="bg-error/10 border-l-2 border-error p-3 mb-6 text-error text-sm font-mono">
            {error}
          </div>
        )}

        <form className="space-y-6" onSubmit={handleLogin}>
          <div className="space-y-2">
            <label className="block text-xs font-mono text-on-surface-variant uppercase tracking-widest">
              Team ID
            </label>
            <input
              type="number"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              className="w-full bg-surface-container border border-outline-variant px-4 py-3 text-on-surface font-mono placeholder:text-outline-variant focus:border-primary transition-colors focus:ring-1 focus:ring-primary/20"
              placeholder="01"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="block text-xs font-mono text-on-surface-variant uppercase tracking-widest">
              Security PIN
            </label>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className="w-full bg-surface-container border border-outline-variant px-4 py-3 text-on-surface font-mono placeholder:text-outline-variant focus:border-primary transition-colors focus:ring-1 focus:ring-primary/20"
              placeholder="••••••••"
              required
            />
          </div>

          <div className="pt-4">
            <button
              type="submit"
              disabled={!teamId || !pin || loading}
              className={`w-full py-4 uppercase font-display font-bold tracking-wider
                bg-gradient-to-br from-primary to-primary-container text-[#111417]
                transition-all duration-200
                ${(!teamId || !pin || loading) ? 'opacity-30 cursor-not-allowed' : 'hover:opacity-90'}
              `}
            >
              {loading ? 'AUTHENTICATING...' : 'ACCESS SYSTEM'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};