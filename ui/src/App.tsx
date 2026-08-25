import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AlertProvider } from './contexts/AlertContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Dashboard from './pages/Dashboard';
import Payments from './pages/Payments';
import Nodes from './pages/Nodes';
import Database from './pages/Database';
import Settings from './pages/Settings';
import Architecture from './pages/Architecture';
import Alerts from './pages/Alerts';
import AuditLogs from './pages/AuditLogs';
import Login from './pages/Login';

const originalFetch = window.fetch;
window.fetch = async (...args) => {
  const [resource, config] = args;
  if (typeof resource === 'string' && resource.startsWith('/api/v1/')) {
    const token = localStorage.getItem('token');
    if (token) {
      const headers = new Headers(config?.headers);
      headers.set('Authorization', `Bearer ${token}`);
      const newConfig = { ...config, headers };
      const response = await originalFetch(resource, newConfig);
      if (response.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
      return response;
    }
  }
  return originalFetch(...args);
};

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <Layout>{children}</Layout>;
};

function App() {
  return (
    <AuthProvider>
      <AlertProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/payments" element={<ProtectedRoute><Payments /></ProtectedRoute>} />
          <Route path="/nodes" element={<ProtectedRoute><Nodes /></ProtectedRoute>} />
          <Route path="/database" element={<ProtectedRoute><Database /></ProtectedRoute>} />
          <Route path="/architecture" element={<ProtectedRoute><Architecture /></ProtectedRoute>} />
          <Route path="/alerts" element={<ProtectedRoute><Alerts /></ProtectedRoute>} />
          <Route path="/audit" element={<ProtectedRoute><AuditLogs /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
        </Routes>
      </AlertProvider>
    </AuthProvider>
  );
}

export default App;
