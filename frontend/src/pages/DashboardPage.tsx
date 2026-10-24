import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Clock, CheckCircle2, AlertTriangle, TrendingUp, MapPin } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import api from '../lib/api';
import type { AnalyticsSummary, TrendPoint } from '../types';
import { Card, CardHeader, CardTitle } from '../components/Card';
import { Skeleton } from '../components/Feedback';
import { formatDate, STATUS_LABELS } from '../lib/constants';

function MetricCard({ icon: Icon, label, value, sub, color = 'text-gray-900' }: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  sub?: string;
  color?: string;
}) {
  return (
    <Card>
      <div className="flex items-start gap-3">
        <div className="p-2 bg-gray-100 rounded-md">
          <Icon className="w-4 h-4 text-gray-600" />
        </div>
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className={`text-2xl font-bold mt-0.5 ${color}`}>{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
      </div>
    </Card>
  );
}

const STATUS_BAR_COLORS: Record<string, string> = {
  submitted: '#9ca3af',
  under_review: '#f59e0b',
  verified: '#3b82f6',
  assigned: '#8b5cf6',
  in_progress: '#06b6d4',
  pending_verification: '#f97316',
  resolved: '#22c55e',
  rejected: '#ef4444',
};

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useQuery<AnalyticsSummary>({
    queryKey: ['analytics-summary'],
    queryFn: () => api.get('/analytics/summary').then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: trends, isLoading: trendsLoading } = useQuery<TrendPoint[]>({
    queryKey: ['analytics-trends'],
    queryFn: () => api.get('/analytics/trends?days=30').then((r) => r.data),
  });

  if (summaryLoading) return <Skeleton className="m-6 h-64" />;

  const statusData = summary
    ? Object.entries(summary.by_status).map(([status, count]) => ({
        status: STATUS_LABELS[status] ?? status,
        count,
        color: STATUS_BAR_COLORS[status] ?? '#9ca3af',
      }))
    : [];

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-base font-semibold text-gray-900">Dashboard</h1>
        <p className="text-xs text-gray-500 mt-0.5">Road damage intelligence overview</p>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={FileText}
          label="Total reports"
          value={summary?.total_reports ?? 0}
        />
        <MetricCard
          icon={TrendingUp}
          label="Last 7 days"
          value={summary?.recent_7_days ?? 0}
          color="text-blue-600"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Overdue"
          value={summary?.overdue_count ?? 0}
          sub="Assigned > 30 days"
          color={summary?.overdue_count ? 'text-red-600' : 'text-gray-900'}
        />
        <MetricCard
          icon={CheckCircle2}
          label="High severity unverified"
          value={summary?.high_severity_unverified ?? 0}
          color={summary?.high_severity_unverified ? 'text-orange-600' : 'text-gray-900'}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Trend */}
        <Card>
          <CardHeader>
            <CardTitle>Reports – last 30 days</CardTitle>
          </CardHeader>
          {trendsLoading ? (
            <Skeleton className="h-40" />
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={trends ?? []} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <defs>
                  <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="count" stroke="#16a34a" fill="url(#trendGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* By status */}
        <Card>
          <CardHeader>
            <CardTitle>Reports by status</CardTitle>
          </CardHeader>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={statusData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <XAxis dataKey="status" tick={{ fontSize: 9 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                {statusData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <a
          href="/coordinator/reports?status=submitted"
          className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-lg
            hover:border-accent hover:shadow-sm transition-all group"
        >
          <FileText className="w-5 h-5 text-gray-400 group-hover:text-accent" />
          <div>
            <p className="text-sm font-medium text-gray-800">New submissions</p>
            <p className="text-xs text-gray-500">Review pending reports</p>
          </div>
        </a>
        <a
          href="/coordinator/map"
          className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-lg
            hover:border-accent hover:shadow-sm transition-all group"
        >
          <MapPin className="w-5 h-5 text-gray-400 group-hover:text-accent" />
          <div>
            <p className="text-sm font-medium text-gray-800">Map view</p>
            <p className="text-xs text-gray-500">See all reports on map</p>
          </div>
        </a>
        <a
          href="/coordinator/analytics"
          className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-lg
            hover:border-accent hover:shadow-sm transition-all group"
        >
          <TrendingUp className="w-5 h-5 text-gray-400 group-hover:text-accent" />
          <div>
            <p className="text-sm font-medium text-gray-800">Analytics</p>
            <p className="text-xs text-gray-500">Trends &amp; insights</p>
          </div>
        </a>
      </div>
    </div>
  );
}
