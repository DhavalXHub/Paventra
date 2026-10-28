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
import HowItWorksPage from './pages/HowItWorksPage';
import RoadIntelligencePage from './pages/RoadIntelligencePage';
import LifecyclePage from './pages/LifecyclePage';
import NotFoundPage from './pages/NotFoundPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

function FullScreenLoading({ message = 'Loading Paventra...' }: { message?: string }) {
  return (
    <div className="min-h-screen bg-[#faf9f6] flex flex-col items-center justify-center p-4">
      <div className="w-8 h-8 border-3 border-stone-200 border-t-[#14462a] rounded-full animate-spin mb-3" />
      <p className="text-xs font-medium text-stone-600 tracking-wide">{message}</p>
    </div>
  );
}

function RequireCoordinator({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isCoordinator, isInitializing } = useAuth();
  const location = useLocation();
  if (isInitializing) {
    return <FullScreenLoading message="Verifying coordinator authorization..." />;
  }
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!isCoordinator) return <Navigate to="/my-reports" replace />;
  return <>{children}</>;
}

function RequireTeam({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isRepairTeam, isCoordinator, isInitializing } = useAuth();
  const location = useLocation();
  if (isInitializing) {
    return <FullScreenLoading message="Verifying team authorization..." />;
  }
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!isRepairTeam && !isCoordinator) return <Navigate to="/my-reports" replace />;
  return <>{children}</>;
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isInitializing } = useAuth();
  const location = useLocation();
  if (isInitializing) {
    return <FullScreenLoading message="Verifying session..." />;
  }
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
              {/* Informational public pages */}
              <Route path="/how-it-works" element={<HowItWorksPage />} />
              <Route path="/road-intelligence" element={<RoadIntelligencePage />} />
              <Route path="/lifecycle" element={<LifecyclePage />} />
              {/* Coordinator */}
              <Route path="/coordinator/*" element={<CoordinatorRoutes />} />
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;
