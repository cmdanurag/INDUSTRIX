import { useEffect } from 'react';
import { useResultsStore, useGameStore } from '../store';
import { StatusChip } from '../components/SharedComponents';

export const Results = () => {
  const { phase } = useGameStore();
  const { cycleNumber, rows, fetchLeaderboard } = useResultsStore();

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard, phase]); // Refetch when phase switches

  const isBackroom = phase === 'backroom' || phase === 'game_over';

  return (
    <div className="flex flex-col h-full space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="font-display text-4xl uppercase tracking-tighter mb-2">
            ROUND RESULTS
          </h1>
          <div className="text-on-surface-variant font-mono text-sm tracking-widest">
            Cycle {cycleNumber} Final Audit
          </div>
        </div>
        
        {isBackroom && (
          <StatusChip label="READ ONLY" variant="warning" />
        )}
      </div>

      <div className="flex-1 bg-surface-low border border-outline-variant p-1">
        <div className="max-h-[80vh] overflow-y-auto">
          <table className="w-full text-left font-mono text-sm border-collapse">
            <thead className="sticky top-0 bg-surface-low z-10 border-b-2 border-outline-variant">
              <tr className="text-on-surface-variant text-[10px] sm:text-xs">
                <th className="py-4 pl-4 font-normal">RANK</th>
                <th className="py-4 px-2 font-normal">TEAM</th>
                <th className="py-4 px-2 font-normal">SCORE</th>
                <th className="py-4 px-2 font-normal">FUNDS</th>
                <th className="py-4 px-2 font-normal">PROFIT</th>
                <th className="py-4 px-2 font-normal">BRAND</th>
                <th className="py-4 px-2 font-normal">QUALITY</th>
                <th className="py-4 px-2 font-normal">PENALTY</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => {
                // Team ID logic (if name matches or ID logic holds). 
                // We'll simulate own-team highlighting by checking name for now since ID isn't in LeaderboardRow
                const isOwnTeam = true; // In real app, match by teamId or teamName. E.g.: `row.team_name.includes(String(teamId))`
                
                return (
                  <tr 
                    key={idx} 
                    className={`border-b border-outline-variant/30 transition-colors 
                      ${isOwnTeam ? 'bg-primary/10 border-l-4 border-l-primary' : 'hover:bg-surface-highest/50'}
                    `}
                  >
                    <td className="py-4 pl-4 font-bold text-lg">
                      {idx === 0 ? <span className="text-tertiary">{row.rank}</span> : row.rank}
                    </td>
                    <td className={`py-4 px-2 ${isOwnTeam ? 'text-primary font-bold' : 'text-on-surface'}`}>
                      {row.team_name}
                    </td>
                    <td className="py-4 px-2 text-on-surface">{row.composite_score?.toFixed(1) || 0}</td>
                    <td className="py-4 px-2 text-on-surface">${row.closing_funds?.toLocaleString()}</td>
                    <td className={`py-4 px-2 ${row.cumulative_profit < 0 ? 'text-error' : 'text-primary'}`}>
                      ${row.cumulative_profit?.toLocaleString()}
                    </td>
                    <td className="py-4 px-2 text-on-surface">{row.brand_score?.toFixed(1) || 0}</td>
                    <td className="py-4 px-2 text-on-surface">{row.quality_avg?.toFixed(1) || 0}</td>
                    <td className="py-4 px-2 text-error">-${row.inventory_penalty?.toLocaleString()}</td>
                  </tr>
                );
              })}
              
              {rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-on-surface-variant">
                    No results available yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
