import React, { useState } from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapPin, LayoutDashboard, FileText, Users, BarChart3, Bell, LogOut, Menu, Video, Home } from 'lucide-react';
import { useAuth } from '../features/auth/AuthContext';
import api from '../lib/api';

const NAV_ITEMS = [
  { to: '/coordinator', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/coordinator/reports', icon: FileText, label: 'Reports' },
  { to: '/coordinator/inspections', icon: Video, label: 'Inspections' },
  { to: '/coordinator/map', icon: MapPin, label: 'Map' },
  { to: '/coordinator/teams', icon: Users, label: 'Teams' },
  { to: '/coordinator/analytics', icon: BarChart3, label: 'Analytics' },
];

export function CoordinatorLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { data: notifications } = useQuery<Array<{ is_read: boolean }>>({
    queryKey: ['notifications'],
    queryFn: () => api.get('/notifications').then((r) => r.data),
    refetchInterval: 30000,
  });
  const unread = notifications?.filter((n) => !n.is_read).length ?? 0;

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-56 bg-white border-r border-gray-200
          flex flex-col transform transition-transform lg:translate-x-0
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} lg:static lg:flex`}
      >
        {/* Logo */}
        <Link
          to="/"
          className="flex items-center gap-2.5 px-5 h-14 border-b border-gray-100 flex-shrink-0 group hover:bg-stone-50 transition-colors"
          title="Return to Public Homepage"
        >
          <div className="w-7 h-7 bg-accent rounded-md flex items-center justify-center">
            <MapPin className="w-4 h-4 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-gray-900 text-sm tracking-tight">Paventra</span>
            <span className="text-[10px] text-stone-500 font-normal">Coordinator Portal</span>
          </div>
        </Link>

        {/* Nav */}
        <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors
                ${isActive
                  ? 'bg-accent-light text-accent font-medium'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
              onClick={() => setSidebarOpen(false)}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}

          <div className="pt-3 mt-3 border-t border-gray-100">
            <Link
              to="/"
              className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-stone-600 hover:bg-stone-100 hover:text-stone-900 transition-colors"
              onClick={() => setSidebarOpen(false)}
            >
              <Home className="w-4 h-4 flex-shrink-0 text-stone-500" />
              <span>Public Homepage</span>
            </Link>
          </div>
        </nav>

        {/* User area */}
        <div className="border-t border-gray-100 p-3">
          <div className="flex items-center gap-2.5 px-2 py-1.5">
            <div className="w-7 h-7 rounded-full bg-accent-light flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-semibold text-accent">
                {user?.full_name?.charAt(0) ?? 'C'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-gray-900 truncate">{user?.full_name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="mt-1 flex items-center gap-2 w-full px-2 py-1.5 text-xs text-gray-500
              hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-white border-b border-gray-200 flex items-center px-4 gap-3 flex-shrink-0">
          <button
            className="lg:hidden p-1.5 rounded-md hover:bg-gray-100 text-gray-500"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1" />
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-600 hover:text-stone-900 hover:bg-stone-100 rounded-md border border-stone-200 transition-colors"
            title="Return to public homepage"
          >
            <Home className="w-3.5 h-3.5 text-stone-500" />
            <span className="hidden sm:inline">Public Home</span>
          </Link>
          <NavLink
            to="/coordinator/notifications"
            className="relative p-1.5 rounded-md hover:bg-gray-100 text-gray-500 transition-colors"
            aria-label={unread ? `${unread} unread notifications` : 'Notifications'}
          >
            <Bell className="w-5 h-5" />
            {unread > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-red-600 text-white text-[10px] leading-4 text-center">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </NavLink>
        </header>

        {/* Page */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
