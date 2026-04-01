import { useEffect } from "react";
import { useGameStore } from "../store/useGameStore";
import { useResultsStore } from "../store/useResultsStore";

export const ResultsPage = () => {
  const { phase, teamName } = useGameStore();
  const { rows, cycleNumber, isFinal, fetchLeaderboard } = useResultsStore();

  useEffect(() => {
    if (phase === "backroom" || phase === "game_over") {
      void fetchLeaderboard();
    }
  }, [phase, fetchLeaderboard]);

  if (!(phase === "backroom" || phase === "game_over")) {
    return <div className="bg-surface-container p-4">Results available in backroom or game over phase.</div>;
  }

  return (
    <div>
      <h1 className="mb-2 text-xl uppercase">Round Results</h1>
      <p className="mb-4 text-on-surface-variant">Cycle {cycleNumber} Final Audit {isFinal ? "(Final)" : ""}</p>
      {phase === "backroom" && (
        <div className="mb-3 inline-block bg-tertiary px-2 py-1 text-xs uppercase text-black">Read Only</div>
      )}
      <div className="overflow-x-auto bg-surface-container">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-high">
            <tr>
              {["RANK", "TEAM", "SCORE", "FUNDS", "PROFIT", "BRAND", "QUALITY", "PENALTY"].map((h) => (
                <th key={h} className="px-3 py-2 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={`${r.rank}-${r.team_name}`} className={r.team_name === teamName ? "bg-surface-highest" : ""}>
                <td className="px-3 py-2">{r.rank}</td>
                <td className="px-3 py-2">{r.team_name}</td>
                <td className="px-3 py-2">{r.composite_score.toFixed(1)}</td>
                <td className="px-3 py-2">{r.closing_funds.toFixed(0)}</td>
                <td className="px-3 py-2">{r.cumulative_profit.toFixed(0)}</td>
                <td className="px-3 py-2">{r.brand_score.toFixed(1)}</td>
                <td className="px-3 py-2">{r.quality_avg.toFixed(1)}</td>
                <td className="px-3 py-2">{r.inventory_penalty.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
