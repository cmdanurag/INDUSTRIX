import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { InventoryPage } from "./pages/InventoryPage";
import { LoginPage } from "./pages/LoginPage";
import { ProductionPage } from "./pages/ProductionPage";
import { RawMaterialsPage } from "./pages/RawMaterialsPage";
import { ResultsPage } from "./pages/ResultsPage";
import { useGameStore } from "./store/useGameStore";
import { setTeamHeaders } from "./api/api";

const PhaseRouter = () => (
  <Routes>
    <Route path="/" element={<RawMaterialsPage />} />
    <Route path="/market" element={<ProductionPage />} />
    <Route path="/inventory" element={<InventoryPage />} />
    <Route path="/event" element={<ResultsPage />} />
    <Route path="*" element={<Navigate to="/" />} />
  </Routes>
);

export const App = () => {
  const { isLoggedIn, pollStatus } = useGameStore();

  useEffect(() => {
    const teamId = localStorage.getItem("teamId");
    const pin = localStorage.getItem("teamPin");
    if (teamId && pin) setTeamHeaders(Number(teamId), pin);
    void pollStatus();
    const id = window.setInterval(() => {
      void pollStatus();
    }, 5000);
    return () => window.clearInterval(id);
  }, [pollStatus]);

  if (!isLoggedIn && !localStorage.getItem("teamId")) {
    return (
      <div className="min-h-screen bg-surface text-on-surface">
        <LoginPage />
      </div>
    );
  }

  return (
    <Layout>
      <PhaseRouter />
    </Layout>
  );
};
