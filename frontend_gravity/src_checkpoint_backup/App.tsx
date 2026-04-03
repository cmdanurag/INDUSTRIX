import { Routes, Route } from 'react-router-dom';
import { SharedLayout } from './components/SharedLayout';
import { Login } from './pages/Login';
import { Procurement } from './pages/Procurement';
import { Production } from './pages/Production';
import { Inventory } from './pages/Inventory';
import { Results } from './pages/Results';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<SharedLayout />}>
        <Route path="/" element={<Procurement />} />
        <Route path="/market" element={<Production />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/event" element={<Results />} />
      </Route>
    </Routes>
  );
}

export default App;
