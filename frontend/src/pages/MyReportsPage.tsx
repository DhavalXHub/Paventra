import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapPin, Plus, FileText, ExternalLink, Calendar, LogOut } from 'lucide-react';
import api from '../lib/api';
import type { ReportListItem } from '../types';
import { useAuth } from '../features/auth/AuthContext';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { EmptyState, Skeleton } from '../components/Feedback';
import { formatDate } from '../lib/constants';

export default function MyReportsPage() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const { data: reports, isLoading } = useQuery<ReportListItem[]>({
    queryKey: ['my-reports'],
    queryFn: () => api.get('/reports/my').then((r) => r.data),
    enabled: isAuthenticated,
  });

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-accent rounded-md flex items-center justify-center">
            <MapPin className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold text-gray-900 text-sm">Paventra</span>
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded ml-2">
            Citizen Portal
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/report">
            <Button size="sm" icon={<Plus className="w-3.5 h-3.5" />}>
              New report
            </Button>
          </Link>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-red-600"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              Welcome, {user?.full_name ?? 'Citizen'}
            </h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Track resolution progress for all road damage reports submitted from your account.
            </p>
          </div>
          <Link to="/track" className="text-xs text-accent hover:underline">
            Search by reference code
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        ) : !reports?.length ? (
          <Card>
            <EmptyState
              icon={<FileText className="w-10 h-10 text-gray-400" />}
              title="No reports submitted yet"
              description="You have not submitted any road damage reports from this account."
              action={
                <Link to="/report">
                  <Button size="sm">Submit road report</Button>
                </Link>
              }
            />
          </Card>
        ) : (
          <div className="space-y-3">
            {reports.map((r) => (
              <div
                key={r.id}
                className="bg-white border border-gray-200 rounded-lg p-4 hover:border-accent/60 transition-colors shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-sm text-gray-900">
                      {r.public_ref}
                    </span>
                    <StatusBadge status={r.status} />
                    {r.severity && <SeverityBadge severity={r.severity} />}
                  </div>

                  <p className="text-xs text-gray-700 font-medium capitalize">
                    {r.damage_type.replace(/_/g, ' ')}
                    {r.address_hint && (
                      <span className="font-normal text-gray-500"> · {r.address_hint}</span>
                    )}
                  </p>

                  <div className="flex items-center gap-2 text-[11px] text-gray-400">
                    <Calendar className="w-3 h-3" />
                    <span>Reported {formatDate(r.created_at)}</span>
                    {r.latitude && r.longitude && (
                      <span className="font-mono">
                        ({r.latitude.toFixed(4)}, {r.longitude.toFixed(4)})
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2 pt-2 sm:pt-0 border-t sm:border-0 border-gray-100">
                  <Link
                    to={`/track/${r.public_ref}`}
                    className="inline-flex items-center gap-1 text-xs text-accent hover:underline font-medium"
                  >
                    Track details
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
