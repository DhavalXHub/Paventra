import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  MapPin, Plus, FileText, ExternalLink, Calendar, LogOut,
  Search, Link as LinkIcon, CheckCircle2, AlertCircle, X, Home, Clock
} from 'lucide-react';
import api from '../lib/api';
import type { ReportListItem } from '../types';
import { useAuth } from '../features/auth/AuthContext';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { EmptyState, Skeleton, Alert } from '../components/Feedback';
import { formatDate } from '../lib/constants';

type StatusFilter = 'all' | 'submitted' | 'under_review' | 'in_progress' | 'resolved';

export default function MyReportsPage() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showClaimModal, setShowClaimModal] = useState(false);
  const [claimRef, setClaimRef] = useState('');
  const [claimToken, setClaimToken] = useState('');
  const [claimEmail, setClaimEmail] = useState('');
  const [claimError, setClaimError] = useState<string | null>(null);
  const [claimSuccess, setClaimSuccess] = useState<string | null>(null);

  const { data: reports, isLoading, error } = useQuery<ReportListItem[]>({
    queryKey: ['my-reports'],
    queryFn: () => api.get('/reports/mine').then((r) => r.data),
    enabled: isAuthenticated,
  });

  const claimMutation = useMutation({
    mutationFn: (payload: { public_ref: string; claim_token?: string; verification_email?: string }) =>
      api.post('/reports/claim', payload).then((r) => r.data),
    onSuccess: (data) => {
      setClaimSuccess(data.message ?? 'Report linked successfully!');
      setClaimError(null);
      setClaimRef('');
      setClaimToken('');
      setClaimEmail('');
      queryClient.invalidateQueries({ queryKey: ['my-reports'] });
      setTimeout(() => {
        setShowClaimModal(false);
        setClaimSuccess(null);
      }, 2500);
    },
    onError: (err: any) => {
      setClaimError(err?.response?.data?.detail ?? 'Failed to claim report. Check details and try again.');
    },
  });

  function handleClaimSubmit(e: React.FormEvent) {
    e.preventDefault();
    setClaimError(null);
    setClaimSuccess(null);
    if (!claimRef.trim()) {
      setClaimError('Please provide the report reference number.');
      return;
    }
    claimMutation.mutate({
      public_ref: claimRef.trim(),
      claim_token: claimToken.trim() || undefined,
      verification_email: claimEmail.trim() || undefined,
    });
  }

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  const filteredReports = (reports ?? []).filter((r) => {
    // Status filter
    if (statusFilter !== 'all') {
      if (statusFilter === 'in_progress') {
        if (!['assigned', 'in_progress', 'pending_verification'].includes(r.status)) return false;
      } else if (statusFilter === 'under_review') {
        if (!['under_review', 'verified'].includes(r.status)) return false;
      } else if (r.status !== statusFilter) {
        return false;
      }
    }
    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchRef = r.public_ref.toLowerCase().includes(q);
      const matchType = r.damage_type.toLowerCase().includes(q);
      const matchAddress = r.address_hint?.toLowerCase().includes(q);
      return matchRef || matchType || matchAddress;
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-[#faf9f6]">
      {/* Global Citizen Navigation Header */}
      <header className="sticky top-0 z-40 bg-white border-b border-stone-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo links to / */}
          <Link
            to="/"
            className="flex items-center gap-2.5 group"
            title="Return to Public Homepage"
          >
            <div className="w-8 h-8 rounded-lg bg-[#14462a] flex items-center justify-center shadow-xs group-hover:bg-[#0f3620] transition-colors">
              <MapPin className="w-4 h-4 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-stone-900 text-sm tracking-tight leading-none">
                Paventra
              </span>
              <span className="text-[10px] text-stone-600 tracking-wider uppercase mt-0.5">
                Citizen Portal
              </span>
            </div>
          </Link>

          {/* Desktop Links */}
          <nav className="hidden sm:flex items-center gap-6 text-sm font-medium">
            <Link to="/" className="text-stone-600 hover:text-stone-900 flex items-center gap-1.5 transition-colors">
              <Home className="w-4 h-4 text-stone-600" />
              <span>Home</span>
            </Link>
            <Link to="/report" className="text-stone-600 hover:text-stone-900 transition-colors">
              Report damage
            </Link>
            <Link to="/track" className="text-stone-600 hover:text-stone-900 transition-colors">
              Track report
            </Link>
            <Link to="/my-reports" className="text-[#14462a] font-semibold border-b-2 border-[#14462a] pb-0.5">
              My reports
            </Link>
          </nav>

          {/* User actions */}
          <div className="flex items-center gap-3">
            <Link to="/report" className="hidden md:inline-flex">
              <Button size="sm" className="bg-[#14462a] hover:bg-[#0f3620] text-white" icon={<Plus className="w-3.5 h-3.5" />}>
                New report
              </Button>
            </Link>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-xs text-stone-600 hover:text-red-600 px-2.5 py-1.5 rounded-lg border border-stone-200 hover:border-red-200 transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Top welcome banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white border border-stone-200 rounded-2xl p-6 shadow-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-stone-900">
                Welcome back, {user?.full_name ?? 'Citizen'}
              </h1>
              <span className="text-[10px] bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold px-2 py-0.5 rounded-full">
                Verified Citizen
              </span>
            </div>
            <p className="text-xs text-stone-600">
              Track progress, view inspection evidence, and monitor municipal road repairs submitted from your account (<strong>{user?.email}</strong>).
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              type="button"
              onClick={() => {
                setShowClaimModal(true);
                setClaimError(null);
                setClaimSuccess(null);
              }}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-stone-700 bg-stone-100 hover:bg-stone-200/80 rounded-xl transition-colors shadow-xs"
            >
              <LinkIcon className="w-3.5 h-3.5 text-stone-600" />
              <span>Claim a guest report</span>
            </button>
            <Link to="/report">
              <Button size="sm" className="bg-[#14462a] hover:bg-[#0f3620] text-white" icon={<Plus className="w-3.5 h-3.5" />}>
                Report road damage
              </Button>
            </Link>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
          {/* Status Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 text-xs font-medium">
            {(
              [
                { id: 'all', label: 'All Reports' },
                { id: 'submitted', label: 'Submitted' },
                { id: 'under_review', label: 'Under Review' },
                { id: 'in_progress', label: 'In Progress' },
                { id: 'resolved', label: 'Resolved' },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                  statusFilter === tab.id
                    ? 'bg-[#14462a] text-white font-semibold shadow-xs'
                    : 'bg-white border border-stone-200 text-stone-600 hover:text-stone-900 hover:bg-stone-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Input */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-stone-600 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search reference or street..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-stone-200 rounded-lg text-stone-900 placeholder-stone-600 focus:outline-none focus:ring-2 focus:ring-[#14462a]"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-600 hover:text-stone-600"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Reports List */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
        ) : error ? (
          <Alert type="error" message="Unable to load your reports. Please refresh or try again later." />
        ) : !reports?.length ? (
          <Card className="rounded-2xl border-stone-200 p-8 text-center">
            <EmptyState
              icon={<FileText className="w-12 h-12 text-stone-600 mx-auto" />}
              title="No reports submitted yet"
              description="You have not submitted any road damage complaints from this account. You can submit one now or link a previously submitted guest report."
              action={
                <div className="flex gap-2 justify-center pt-2">
                  <Link to="/report">
                    <Button size="sm" className="bg-[#14462a] text-white">Report road damage</Button>
                  </Link>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setShowClaimModal(true)}
                  >
                    Claim guest report
                  </Button>
                </div>
              }
            />
          </Card>
        ) : !filteredReports.length ? (
          <div className="bg-white border border-stone-200 rounded-2xl p-8 text-center space-y-2">
            <p className="text-sm font-semibold text-stone-800">No matching reports found</p>
            <p className="text-xs text-stone-600">
              No reports match your selected status filter &quot;{statusFilter}&quot; or search query.
            </p>
            <button
              onClick={() => {
                setStatusFilter('all');
                setSearchQuery('');
              }}
              className="text-xs font-semibold text-[#14462a] hover:underline pt-2 block mx-auto"
            >
              Reset filters
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredReports.map((r) => (
              <div
                key={r.id}
                className="bg-white border border-stone-200 rounded-2xl p-5 hover:border-[#14462a]/50 transition-all shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="font-mono font-bold text-sm text-stone-900 tracking-wider">
                      {r.public_ref}
                    </span>
                    <StatusBadge status={r.status} />
                    {r.severity && <SeverityBadge severity={r.severity} />}
                  </div>

                  <p className="text-xs text-stone-800 font-medium capitalize">
                    {r.damage_type.replace(/_/g, ' ')}
                    {r.address_hint && (
                      <span className="font-normal text-stone-600"> · {r.address_hint}</span>
                    )}
                  </p>

                  <div className="flex items-center gap-3 text-[11px] text-stone-600 flex-wrap">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      Reported {formatDate(r.created_at)}
                    </span>
                    {r.latitude && r.longitude && (
                      <span className="flex items-center gap-1 font-mono">
                        <MapPin className="w-3 h-3 text-stone-600" />
                        {r.latitude.toFixed(4)}, {r.longitude.toFixed(4)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2.5 pt-3 sm:pt-0 border-t sm:border-0 border-stone-100">
                  <Link
                    to={`/track/${r.public_ref}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-[#14462a] bg-stone-50 hover:bg-stone-100 border border-stone-200 rounded-lg transition-colors"
                  >
                    <span>View Timeline & Updates</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Claim Modal */}
      {showClaimModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-stone-200 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-stone-100">
              <div className="flex items-center gap-2">
                <LinkIcon className="w-4 h-4 text-[#14462a]" />
                <h3 className="text-sm font-bold text-stone-900">Claim an Existing Report</h3>
              </div>
              <button
                onClick={() => setShowClaimModal(false)}
                className="text-stone-600 hover:text-stone-700 p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-stone-600 leading-relaxed">
              If you previously submitted a report as a guest, you can securely link it to this account using your reference code and claim token (or submitted email).
            </p>

            {claimError && <Alert type="error" message={claimError} />}
            {claimSuccess && <Alert type="success" message={claimSuccess} />}

            <form onSubmit={handleClaimSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  Report Reference <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g. PAV-XXXXXXXX"
                  value={claimRef}
                  onChange={(e) => setClaimRef(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 text-xs font-mono uppercase bg-white border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14462a]"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  Claim Token (Provided at submission)
                </label>
                <input
                  type="text"
                  placeholder="Paste token or leave empty if using email"
                  value={claimToken}
                  onChange={(e) => setClaimToken(e.target.value)}
                  className="w-full px-3 py-2 text-xs font-mono bg-white border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14462a]"
                />
              </div>

              <div className="relative flex items-center justify-center my-1">
                <div className="border-t border-stone-200 w-full" />
                <span className="bg-white px-2 text-[10px] uppercase font-semibold text-stone-600">
                  Or verify with email
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-stone-700 mb-1">
                  Email Used When Reporting
                </label>
                <input
                  type="email"
                  placeholder="e.g. guest@example.com"
                  value={claimEmail}
                  onChange={(e) => setClaimEmail(e.target.value)}
                  className="w-full px-3 py-2 text-xs bg-white border border-stone-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#14462a]"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setShowClaimModal(false)}
                  className="flex-1 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={claimMutation.isPending}
                  className="flex-1 bg-[#14462a] hover:bg-[#0f3620] text-white text-xs font-semibold"
                >
                  Link Report
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
