import { useEffect } from "react";
import { ComponentTabs } from "../components/ComponentTabs";
import { SendDecisionsButton } from "../components/SendDecisionsButton";
import { useGameStore } from "../store/useGameStore";
import { useInventoryStore } from "../store/useInventoryStore";
import { useProcurementStore } from "../store/useProcurementStore";

const costMult: Record<"road" | "rail" | "air", number> = { road: 1, rail: 1.4, air: 2.5 };

export const RawMaterialsPage = () => {
  const phase = useGameStore((s) => s.phase);
  const { funds, fetchInventory } = useInventoryStore();
  const { selectedComponent, setComponent, decisions, setDecision, hydrate, submit, lastSavedAt } =
    useProcurementStore();

  useEffect(() => {
    void hydrate();
    void fetchInventory();
  }, [hydrate, fetchInventory]);

  const total = Object.values(decisions).reduce((acc, d) => {
    return acc + d.quantity * d.source_id * costMult[d.transport];
  }, 0);

  const selected = decisions[selectedComponent];
  const editable = phase === "procurement_open";

  return (
    <div>
      <h1 className="mb-3 text-xl uppercase">Procurement</h1>
      <ComponentTabs selected={selectedComponent} onSelect={setComponent} />
      <div className="grid gap-4 md:grid-cols-2">
        <section className="bg-surface-container p-4">
          <label className="mb-1 block text-xs uppercase text-on-surface-variant">Source Id</label>
          <input
            className="mb-3 w-full bg-surface-high p-2"
            type="number"
            min={1}
            value={selected.source_id}
            disabled={!editable}
            onChange={(e) => setDecision(selectedComponent, { source_id: Number(e.target.value) })}
          />
          <label className="mb-1 block text-xs uppercase text-on-surface-variant">Quantity</label>
          <input
            className="mb-3 w-full bg-surface-high p-2"
            type="number"
            min={0}
            max={10000}
            value={selected.quantity}
            disabled={!editable}
            onChange={(e) => setDecision(selectedComponent, { quantity: Number(e.target.value) })}
          />
          <div className="grid grid-cols-3 gap-2">
            {(["road", "rail", "air"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                disabled={!editable}
                onClick={() => setDecision(selectedComponent, { transport: mode })}
                className={`p-2 uppercase ${selected.transport === mode ? "bg-surface-highest text-primary" : "bg-surface-high text-on-surface-variant"}`}
              >
                {mode}
              </button>
            ))}
          </div>
          {total > 0.8 * funds && (
            <div className="mt-3 border-l-4 border-tertiary bg-surface-high p-2 text-sm">
              Spending exceeds 80% of available funds
            </div>
          )}
          {total > funds && (
            <div className="mt-2 border-l-4 border-error bg-surface-high p-2 text-sm text-error">
              Overspending: total cost exceeds balance
            </div>
          )}
        </section>
        <section className="bg-surface-container p-4 text-sm">
          <p className="mb-2 uppercase text-on-surface-variant">Supplier Details</p>
          <p>Selected Source ID: {selected.source_id}</p>
          <p>Transport: {selected.transport.toUpperCase()}</p>
          <p>Component Cost (estimated): {(selected.quantity * selected.source_id * costMult[selected.transport]).toFixed(2)}</p>
          <p className="mt-2">Global Funds Remaining: {(funds - total).toFixed(2)}</p>
          <p className="mt-2 text-on-surface-variant">Last saved: {lastSavedAt || "-"}</p>
        </section>
      </div>
      <div className="mt-4 bg-surface-container p-4">
        <p className="mb-2 text-sm">Total Procurement Cost: {total.toFixed(2)}</p>
        <SendDecisionsButton onClick={() => void submit()} disabled={!editable} />
      </div>
    </div>
  );
};
