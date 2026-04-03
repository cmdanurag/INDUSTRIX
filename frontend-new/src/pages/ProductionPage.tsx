import { useEffect } from "react";
import { ComponentTabs } from "../components/ComponentTabs";
import { SendDecisionsButton } from "../components/SendDecisionsButton";
import { useGameStore } from "../store/useGameStore";
import { useProductionStore } from "../store/useProductionStore";
import type { RndFocus } from "../types/game";

const maintenanceCost = { none: 0, basic: 500, full: 1500 } as const;
const wageCost = { below_market: 300, market: 500, above_market: 750 } as const;

export const ProductionPage = () => {
  const phase = useGameStore((s) => s.phase);
  const {
    selectedComponent,
    setComponent,
    componentDecisions,
    setMaintenance,
    setRnd,
    wageLevel,
    targetHeadcount,
    upgradeAutomation,
    setWage,
    setHeadcount,
    setAutomation,
    hydrate,
    submit,
    lastSavedAt,
  } = useProductionStore();

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  const curr = componentDecisions[selectedComponent];
  const editable = phase === "production_open";

  const totalMaintenance = Object.values(componentDecisions).reduce(
    (acc, c) => acc + maintenanceCost[c.maintenance],
    0
  );
  const totalRnd = Object.values(componentDecisions).reduce(
    (acc, c) => acc + (c.rnd_invest ? c.rnd_invest.levels * 10000 : 0),
    0
  );
  const workforce = targetHeadcount * wageCost[wageLevel];
  const total = totalMaintenance + totalRnd + workforce;

  return (
    <div>
      <h1 className="mb-3 text-xl uppercase">Production</h1>
      <ComponentTabs selected={selectedComponent} onSelect={setComponent} />
      <div className="grid gap-4 md:grid-cols-2">
        <section className="bg-surface-container p-4">
          <p className="mb-1 text-xs uppercase text-on-surface-variant">Maintenance</p>
          <div className="mb-3 grid grid-cols-3 gap-2">
            {(["none", "basic", "full"] as const).map((m) => (
              <button
                key={m}
                type="button"
                disabled={!editable}
                onClick={() => setMaintenance(selectedComponent, m)}
                className={`p-2 uppercase ${curr.maintenance === m ? "bg-surface-highest text-primary" : "bg-surface-high text-on-surface-variant"}`}
              >
                {m}
              </button>
            ))}
          </div>
          <label className="mb-1 block text-xs uppercase text-on-surface-variant">R&D levels (0-5)</label>
          <input
            className="mb-3 w-full bg-surface-high p-2"
            type="number"
            min={0}
            max={5}
            value={curr.rnd_invest?.levels ?? 0}
            disabled={!editable}
            onChange={(e) => setRnd(selectedComponent, Number(e.target.value), (curr.rnd_invest?.focus ?? "quality") as RndFocus)}
          />
          <label className="mb-1 block text-xs uppercase text-on-surface-variant">R&D focus</label>
          <select
            className="mb-3 w-full bg-surface-high p-2"
            disabled={!editable}
            value={curr.rnd_invest?.focus ?? "quality"}
            onChange={(e) => setRnd(selectedComponent, curr.rnd_invest?.levels ?? 1, e.target.value as RndFocus)}
          >
            <option value="quality">quality</option>
            <option value="consistency">consistency</option>
            <option value="yield">yield</option>
          </select>
          <p className="mb-1 text-xs uppercase text-on-surface-variant">Wage level</p>
          <div className="mb-3 grid grid-cols-3 gap-2">
            {(["below_market", "market", "above_market"] as const).map((w) => (
              <button
                key={w}
                type="button"
                disabled={!editable}
                onClick={() => setWage(w)}
                className={`p-2 text-xs uppercase ${wageLevel === w ? "bg-surface-highest text-primary" : "bg-surface-high text-on-surface-variant"}`}
              >
                {w}
              </button>
            ))}
          </div>
          <label className="mb-1 block text-xs uppercase text-on-surface-variant">Headcount</label>
          <input
            className="mb-3 w-full bg-surface-high p-2"
            type="number"
            min={0}
            max={500}
            value={targetHeadcount}
            disabled={!editable}
            onChange={(e) => setHeadcount(Number(e.target.value))}
          />
          <p className="mb-1 text-xs uppercase text-on-surface-variant">Automation</p>
          <div className="grid grid-cols-3 gap-2">
            {(["manual", "semi_auto", "full_auto"] as const).map((a) => (
              <button
                key={a}
                type="button"
                disabled={!editable}
                onClick={() => setAutomation(a)}
                className={`p-2 text-xs uppercase ${upgradeAutomation === a ? "bg-surface-highest text-primary" : "bg-surface-high text-on-surface-variant"}`}
              >
                {a}
              </button>
            ))}
          </div>
        </section>
        <section className="bg-surface-container p-4 text-sm">
          <p>Maintenance Cost: {totalMaintenance.toFixed(2)}</p>
          <p>R&D Cost: {totalRnd.toFixed(2)}</p>
          <p>Workforce Cost: {workforce.toFixed(2)}</p>
          <p className="mt-2 font-semibold">Total Production Cost: {total.toFixed(2)}</p>
          <p className="mt-2 text-on-surface-variant">Last saved: {lastSavedAt || "-"}</p>
        </section>
      </div>
      <div className="mt-4 bg-surface-container p-4">
        <SendDecisionsButton onClick={() => void submit()} disabled={!editable} />
      </div>
    </div>
  );
};
