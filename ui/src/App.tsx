import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AlertProvider } from './contexts/AlertContext';
import Dashboard from './pages/Dashboard';
import Payments from './pages/Payments';
import Nodes from './pages/Nodes';
import Database from './pages/Database';
import Settings from './pages/Settings';
import Architecture from './pages/Architecture';
import Alerts from './pages/Alerts';

function App() {
  return (
    <AlertProvider>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/nodes" element={<Nodes />} />
          <Route path="/database" element={<Database />} />
          <Route path="/architecture" element={<Architecture />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </AlertProvider>
  );
}

export default App;
