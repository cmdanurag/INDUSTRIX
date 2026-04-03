import { Routes, Route } from 'react-router-dom';
import { SharedLayout } from './components/SharedLayout';
import { Login } from './pages/Login';
import { ActivePhaseDispatcher } from './pages/ActivePhaseDispatcher';
import { Inventory } from './pages/Inventory';
import { Results } from './pages/Results';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<SharedLayout />}>
        <Route path="/" element={<ActivePhaseDispatcher />} />
        <Route path="/market" element={<ActivePhaseDispatcher />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/event" element={<Results />} />
      </Route>
    </Routes>
  );
}

export default App;
