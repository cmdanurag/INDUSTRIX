import { useEffect } from "react";
import { useGameStore } from "../store/useGameStore";
import { useInventoryStore } from "../store/useInventoryStore";

export const InventoryPage = () => {
  const phase = useGameStore((s) => s.phase);
  const {
    funds,
    brandScore,
    brandTier,
    droneStockTotal,
    rawMaterialStocks,
    droneBreakdown,
    fetchInventory,
    scrapRejectUnits,
  } = useInventoryStore();

  useEffect(() => {
    void fetchInventory();
  }, [fetchInventory]);

  return (
    <div>
      <h1 className="mb-3 text-xl uppercase">Inventory</h1>
      <div className="mb-4 grid gap-4 md:grid-cols-2">
        <div className="bg-surface-container p-4">
          <p className="text-xs uppercase text-on-surface-variant">Global Funds</p>
          <p className={`text-2xl ${funds < 0 ? "text-error" : ""}`}>{funds.toFixed(2)}</p>
        </div>
        <div className="bg-surface-container p-4">
          <p className="text-xs uppercase text-on-surface-variant">Brand Score</p>
          <p className="text-2xl">{brandScore.toFixed(1)}</p>
          <p className="uppercase text-on-surface-variant">{brandTier}</p>
        </div>
      </div>
      <div className="mb-4 bg-surface-container p-4">
        <p className="mb-2 text-sm uppercase">Raw Materials Stock</p>
        {Object.entries(rawMaterialStocks).map(([k, v]) => (
          <div key={k} className="flex justify-between border-b border-surface-high py-1 text-sm">
            <span>{k}</span>
            <span>{v}</span>
          </div>
        ))}
      </div>
      <div className="mb-4 bg-surface-container p-4">
        <p className="text-sm">Total Units: {droneStockTotal}</p>
        <p className="text-sm">Reject: {droneBreakdown.reject}</p>
        <p className="text-sm">Substandard: {droneBreakdown.substandard}</p>
        <p className="text-sm">Standard: {droneBreakdown.standard}</p>
        <p className="text-sm">Premium: {droneBreakdown.premium}</p>
      </div>
      <button
        type="button"
        disabled={phase !== "sales_open"}
        onClick={() => void scrapRejectUnits()}
        className="bg-surface-container px-4 py-2 uppercase disabled:opacity-50"
      >
        Scrap Reject Units
      </button>
    </div>
  );
};
