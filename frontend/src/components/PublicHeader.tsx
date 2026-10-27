import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MapPin, User, Menu, X, ArrowRight, ShieldCheck } from 'lucide-react';
import { useAuth } from '../features/auth/AuthContext';

export function PublicHeader({ current }: { current?: 'home' | 'report' | 'track' | 'account' | 'how-it-works' | 'road-intelligence' | 'lifecycle' }) {
  const { isAuthenticated, isCoordinator, isRepairTeam, user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const accountHref = isCoordinator
    ? '/coordinator'
    : isRepairTeam
    ? '/team/jobs'
    : '/my-reports';

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-stone-200 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo & Wordmark */}
          <Link
            to="/"
            className="flex items-center gap-2.5 group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#14462a] rounded-lg p-1"
          >
            <div className="w-8 h-8 rounded-lg bg-[#14462a] flex items-center justify-center shadow-sm group-hover:bg-[#0f3620] transition-colors">
              <MapPin className="w-4 h-4 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-stone-900 text-base tracking-tight leading-none">
                Paventra
              </span>
              <span className="text-[10px] font-medium text-stone-600 tracking-wider uppercase mt-0.5">
                Road Intelligence
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
            <Link
              to="/"
              className={`transition-colors ${
                current === 'home' || location.pathname === '/'
                  ? 'text-[#14462a] font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Home
            </Link>
            <Link
              to="/how-it-works"
              className={`transition-colors ${
                current === 'how-it-works' || location.pathname === '/how-it-works'
                  ? 'text-[#14462a] font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              How it works
            </Link>
            <Link
              to="/road-intelligence"
              className={`transition-colors ${
                current === 'road-intelligence' || location.pathname === '/road-intelligence'
                  ? 'text-[#14462a] font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Road intelligence
            </Link>
            <Link
              to="/lifecycle"
              className={`transition-colors ${
                current === 'lifecycle' || location.pathname === '/lifecycle'
                  ? 'text-[#14462a] font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Lifecycle
            </Link>
            <Link
              to="/track"
              className={`transition-colors ${
                current === 'track' || location.pathname.startsWith('/track')
                  ? 'text-[#14462a] font-semibold'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
            >
              Track report
            </Link>

            {isAuthenticated && !isCoordinator && !isRepairTeam && (
              <Link
                to="/my-reports"
                className={`transition-colors ${
                  location.pathname === '/my-reports'
                    ? 'text-[#14462a] font-semibold'
                    : 'text-stone-600 hover:text-stone-900'
                }`}
              >
                My reports
              </Link>
            )}

            <div className="h-4 w-px bg-stone-200" />

            {/* Auth / Account */}
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <Link
                  to={accountHref}
                  className="flex items-center gap-1.5 text-stone-700 hover:text-[#14462a] transition-colors"
                  title="View portal / reports"
                >
                  <div className="w-6 h-6 rounded-full bg-stone-100 border border-stone-200 flex items-center justify-center">
                    <User className="w-3.5 h-3.5 text-stone-600" />
                  </div>
                  <span className="text-xs font-semibold">
                    {isCoordinator
                      ? 'Coordinator'
                      : isRepairTeam
                      ? 'Work orders'
                      : user?.full_name?.split(' ')[0] || 'My reports'}
                  </span>
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    window.location.href = '/';
                  }}
                  className="text-xs text-stone-500 hover:text-red-600 transition-colors"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="text-stone-600 hover:text-stone-900 transition-colors text-xs font-semibold px-2 py-1"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  className="text-xs font-medium text-stone-600 hover:text-stone-900 border border-stone-200 rounded-md px-2 py-1"
                >
                  Register
                </Link>
              </div>
            )}

            {/* Primary Action Button */}
            <Link
              to="/report"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#14462a] text-white text-xs font-semibold hover:bg-[#0f3620] active:scale-95 shadow-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#14462a]"
            >
              <span>Report road damage</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </nav>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <Link
              to="/report"
              className="inline-flex items-center px-3 py-1.5 rounded-lg bg-[#14462a] text-white text-xs font-semibold hover:bg-[#0f3620] transition-colors"
            >
              Report
            </Link>
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-stone-200 bg-white px-4 py-4 space-y-3 shadow-lg">
          <Link
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-sm font-medium text-stone-700 hover:text-[#14462a] py-1.5"
          >
            Home
          </Link>
          <Link
            to="/how-it-works"
            onClick={() => setMobileMenuOpen(false)}
            className={`block text-sm font-medium py-1.5 ${
              location.pathname === '/how-it-works'
                ? 'text-[#14462a] font-semibold'
                : 'text-stone-700 hover:text-[#14462a]'
            }`}
          >
            How it works
          </Link>
          <Link
            to="/road-intelligence"
            onClick={() => setMobileMenuOpen(false)}
            className={`block text-sm font-medium py-1.5 ${
              location.pathname === '/road-intelligence'
                ? 'text-[#14462a] font-semibold'
                : 'text-stone-700 hover:text-[#14462a]'
            }`}
          >
            Road intelligence
          </Link>
          <Link
            to="/lifecycle"
            onClick={() => setMobileMenuOpen(false)}
            className={`block text-sm font-medium py-1.5 ${
              location.pathname === '/lifecycle'
                ? 'text-[#14462a] font-semibold'
                : 'text-stone-700 hover:text-[#14462a]'
            }`}
          >
            Repair lifecycle
          </Link>
          <Link
            to="/track"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-sm font-medium text-stone-700 hover:text-[#14462a] py-1.5"
          >
            Track a report
          </Link>
          {isAuthenticated && !isCoordinator && !isRepairTeam && (
            <Link
              to="/my-reports"
              onClick={() => setMobileMenuOpen(false)}
              className="block text-sm font-medium text-[#14462a] font-semibold py-1.5"
            >
              My reports
            </Link>
          )}

          <div className="pt-2 border-t border-stone-100 flex flex-col gap-2">
            {isAuthenticated ? (
              <Link
                to={accountHref}
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center gap-2 py-2 text-sm font-semibold text-[#14462a]"
              >
                <User className="w-4 h-4" />
                <span>
                  {isCoordinator
                    ? 'Coordinator Portal'
                    : isRepairTeam
                    ? 'Repair Operations'
                    : 'My Reports'}
                </span>
              </Link>
            ) : (
              <div className="flex gap-2 pt-1">
                <Link
                  to="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 text-center py-2 text-xs font-semibold text-stone-700 bg-stone-100 rounded-lg"
                >
                  Sign in
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex-1 text-center py-2 text-xs font-semibold text-[#14462a] border border-[#14462a] rounded-lg"
                >
                  Citizen register
                </Link>
              </div>
            )}
            <Link
              to="/report"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full text-center py-2.5 rounded-lg bg-[#14462a] text-white text-xs font-semibold hover:bg-[#0f3620]"
            >
              Report road damage now
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
