import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './features/auth/AuthContext';
import { CoordinatorLayout } from './components/CoordinatorLayout';

// Pages
import ReportPage from './pages/ReportPage';
import TrackPage from './pages/TrackPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ReportsListPage from './pages/ReportsListPage';
import ReportDetailPage from './pages/ReportDetailPage';
import MapPage from './pages/MapPage';
import TeamsPage from './pages/TeamsPage';
import AnalyticsPage from './pages/AnalyticsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

function RequireCoordinator({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isCoordinator } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isCoordinator) return <Navigate to="/report" replace />;
  return <>{children}</>;
}

function CoordinatorRoutes() {
  return (
    <RequireCoordinator>
      <CoordinatorLayout>
        <Routes>
          <Route index element={<DashboardPage />} />
          <Route path="reports" element={<ReportsListPage />} />
          <Route path="reports/:id" element={<ReportDetailPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="teams" element={<TeamsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="*" element={<Navigate to="/coordinator" replace />} />
        </Routes>
      </CoordinatorLayout>
    </RequireCoordinator>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/" element={<Navigate to="/report" replace />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="/track" element={<TrackPage />} />
            <Route path="/track/:ref" element={<TrackPage />} />
            <Route path="/login" element={<LoginPage />} />
            {/* Coordinator */}
            <Route path="/coordinator/*" element={<CoordinatorRoutes />} />
            <Route path="*" element={<Navigate to="/report" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
