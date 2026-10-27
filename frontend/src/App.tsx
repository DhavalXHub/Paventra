import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './features/auth/AuthContext';
import { CoordinatorLayout } from './components/CoordinatorLayout';
import { ErrorBoundary } from './components/ErrorBoundary';

// Pages
import HomePage from './pages/HomePage';
import ReportPage from './pages/ReportPage';
import TrackPage from './pages/TrackPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ReportsListPage from './pages/ReportsListPage';
import ReportDetailPage from './pages/ReportDetailPage';
import MapPage from './pages/MapPage';
import TeamsPage from './pages/TeamsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import NotificationsPage from './pages/NotificationsPage';
import InspectionsPage from './pages/InspectionsPage';
import RegisterPage from './pages/RegisterPage';
import MyReportsPage from './pages/MyReportsPage';
import TeamJobsPage from './pages/TeamJobsPage';

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
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!isCoordinator) return <Navigate to="/report" replace />;
  return <>{children}</>;
}

function RequireTeam({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isRepairTeam, isCoordinator } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!isRepairTeam && !isCoordinator) return <Navigate to="/report" replace />;
  return <>{children}</>;
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
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
          <Route path="inspections" element={<InspectionsPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="teams" element={<TeamsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="*" element={<Navigate to="/coordinator" replace />} />
        </Routes>
      </CoordinatorLayout>
    </RequireCoordinator>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public */}
              <Route path="/" element={<HomePage />} />
              <Route path="/report" element={<ReportPage />} />
              <Route path="/track" element={<TrackPage />} />
              <Route path="/track/:ref" element={<TrackPage />} />
              <Route path="/my-reports" element={<RequireAuth><MyReportsPage /></RequireAuth>} />
              <Route path="/team/jobs" element={<RequireTeam><TeamJobsPage /></RequireTeam>} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              {/* Coordinator */}
              <Route path="/coordinator/*" element={<CoordinatorRoutes />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;
