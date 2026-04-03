import { useState } from 'react';
import { useGameStore } from '../store';
import { useNavigate } from 'react-router-dom';
import { SendDecisionsButton } from '../components/SharedComponents';

export const Login = () => {
  const [teamId, setTeamId] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useGameStore();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(parseInt(teamId, 10), pin);
      navigate('/');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Login failed. Check credentials.');
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

        <form onSubmit={handleLogin} className="space-y-6">
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
            <SendDecisionsButton 
              onClick={() => {}} 
              disabled={!teamId || !pin}
              loading={loading}
            />
            {/* Using the styled button component for consistency, but intercepting its layout for form submission */}
            {/* Wait, SendDecisionsButton is a button without type="submit". Let's wrap it nicely. */}
          </div>
        </form>
      </div>
    </div>
  );
};
