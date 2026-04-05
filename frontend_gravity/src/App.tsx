import { Routes, Route, Navigate } from 'react-router-dom';
import { SharedLayout } from './components/SharedLayout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { ActivePhaseDispatcher } from './pages/ActivePhaseDispatcher';
import { Market } from './pages/Market';
import { Inventory } from './pages/Inventory';
import { Events } from './pages/Events';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={
        <ProtectedRoute>
          <SharedLayout />
        </ProtectedRoute>
      }>
        <Route path="/" element={<ActivePhaseDispatcher />} />
        <Route path="/market" element={<Market />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/event" element={<Events />} />
      </Route>
      {/* Redirect any unknown routes to login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default App;