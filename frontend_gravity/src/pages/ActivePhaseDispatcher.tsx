import React from 'react';
import { useGameStore } from '../store';
import { Procurement } from './Procurement';
import { Production } from './Production';
import { Sales } from './Sales';
import { Results } from './Results';

export const ActivePhaseDispatcher: React.FC = () => {
  const { phase } = useGameStore();

  switch (phase) {
    case 'procurement_open':
      return <Procurement />;
    case 'production_open':
      return <Production />;
    case 'sales_open':
      return <Sales />;
    case 'backroom':
      return <Results />;
    case 'game_over':
      return <Results />;
    case 'waiting_for_first_cycle':
      return (
        <div className="flex flex-col items-center justify-center h-full space-y-4">
          <div className="text-4xl animate-pulse text-tertiary">...</div>
          <h2 className="text-2xl font-display uppercase tracking-widest text-on-surface">Game starting soon</h2>
          <p className="text-on-surface-variant font-mono">Waiting for organiser to create the first cycle.</p>
        </div>
      );
    case 'no_active_game':
    case '':
      return (
        <div className="flex flex-col items-center justify-center h-full space-y-4">
          <h2 className="text-2xl font-display text-error uppercase tracking-widest">No Active Game</h2>
          <p className="text-on-surface-variant font-mono">Contact the organiser. Connection might be establishing.</p>
        </div>
      );
    default:
      return (
        <div className="flex flex-col items-center justify-center h-full space-y-4">
          <h2 className="text-2xl font-display text-error uppercase tracking-widest">Unknown Phase</h2>
          <p className="text-on-surface-variant font-mono">Unrecognized phase state: {phase}</p>
        </div>
      );
  }
};
