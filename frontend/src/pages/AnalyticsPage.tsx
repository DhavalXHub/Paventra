import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend
} from 'recharts';
import api from '../lib/api';
import type { AnalyticsSummary, TrendPoint } from '../types';
import { Card, CardHeader, CardTitle } from '../components/Card';
import { Skeleton } from '../components/Feedback';
import { STATUS_LABELS } from '../lib/constants';

const SEV_COLORS: Record<string, string> = {
  low: '#22c55e', moderate: '#f59e0b', high: '#f97316', critical: '#ef4444', None: '#9ca3af'
};

const STATUS_COLORS: Record<string, string> = {
  submitted: '#9ca3af', under_review: '#f59e0b', verified: '#3b82f6',
  assigned: '#8b5cf6', in_progress: '#06b6d4', pending_verification: '#f97316',
  resolved: '#22c55e', rejected: '#ef4444',
};

export default function AnalyticsPage() {
  const { data: summary, isLoading } = useQuery<AnalyticsSummary>({
    queryKey: ['analytics-summary'],
    queryFn: () => api.get('/analytics/summary').then((r) => r.data),
  });

  const { data: trends } = useQuery<TrendPoint[]>({
    queryKey: ['analytics-trends-90'],
    queryFn: () => api.get('/analytics/trends?days=90').then((r) => r.data),
  });

  const { data: batchAnalytics } = useQuery({
    queryKey: ['analytics-batch'],
    queryFn: () => api.get('/analytics/batch').then((r) => r.data),
    staleTime: 60000,
  });

  if (isLoading) return <Skeleton className="m-6 h-96" />;

  const statusData = summary
    ? Object.entries(summary.by_status).map(([k, v]) => ({
        name: STATUS_LABELS[k] ?? k, value: v, color: STATUS_COLORS[k] ?? '#9ca3af'
      }))
    : [];

  const severityData = summary
    ? Object.entries(summary.by_severity).map(([k, v]) => ({
        name: k === 'None' ? 'Unknown' : k.charAt(0).toUpperCase() + k.slice(1),
        value: v, fill: SEV_COLORS[k] ?? '#9ca3af'
      }))
    : [];

  const sourceData = summary
    ? Object.entries(summary.by_source).map(([k, v]) => ({
        name: k.charAt(0).toUpperCase() + k.slice(1), value: v
      }))
    : [];

  return (
    <div className="p-6 space-y-5 max-w-7xl">
      <div>
        <h1 className="text-base font-semibold text-gray-900">Analytics</h1>
        <p className="text-xs text-gray-500">Aggregated road damage statistics</p>
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Total reports', value: summary?.total_reports ?? 0 },
          { label: 'Last 7 days', value: summary?.recent_7_days ?? 0 },
          { label: 'Overdue cases', value: summary?.overdue_count ?? 0 },
          { label: 'High severity unverified', value: summary?.high_severity_unverified ?? 0 },
        ].map((m) => (
          <Card key={m.label} className="text-center">
            <p className="text-2xl font-bold text-gray-900">{m.value}</p>
            <p className="text-xs text-gray-500 mt-0.5">{m.label}</p>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* By status */}
        <Card>
          <CardHeader><CardTitle>By status</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={statusData} margin={{ left: -20, bottom: 20 }}>
              <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-30} textAnchor="end" />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {statusData.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* By severity */}
        <Card>
          <CardHeader><CardTitle>By severity</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={severityData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                {severityData.map((e, i) => <Cell key={i} fill={e.fill} />)}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        {/* Trend */}
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Reports over last 90 days</CardTitle></CardHeader>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={trends ?? []} margin={{ left: -20 }}>
              <XAxis dataKey="date" tick={{ fontSize: 9 }} />
              <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12 }} />
              <Bar dataKey="count" fill="#16a34a" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Source breakdown */}
      <Card>
        <CardHeader><CardTitle>Report source breakdown</CardTitle></CardHeader>
        <div className="flex gap-8">
          {sourceData.map((s) => (
            <div key={s.name} className="text-center">
              <p className="text-2xl font-bold text-gray-900">{s.value}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.name}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Big Data Batch Analytics & Hotspot Clustering */}
      {batchAnalytics && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Batch Hotspot Clustering & Parity Analytics</CardTitle>
              <p className="text-xs text-gray-500 mt-0.5">
                Aggregated spatial clusters (0.01° grid) & turnaround performance across {batchAnalytics.input_records_count ?? 150} reports
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded border border-gray-200">
                Engine: {batchAnalytics.spark_or_fallback_results?.engine ?? 'REFERENCE_PANDAS'}
              </span>
              {batchAnalytics.parity_confirmed && (
                <span className="text-[11px] bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded font-medium">
                  Parity Verified: True
                </span>
              )}
            </div>
          </CardHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-gray-50 rounded-md border border-gray-200">
                <p className="text-xs text-gray-500">Avg Resolution Turnaround</p>
                <p className="text-lg font-bold text-gray-900 mt-0.5">
                  {batchAnalytics.spark_or_fallback_results?.average_repair_duration_days ?? 0} days
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-md border border-gray-200">
                <p className="text-xs text-gray-500">Overdue Reports (&gt; 30d)</p>
                <p className="text-lg font-bold text-amber-600 mt-0.5">
                  {batchAnalytics.spark_or_fallback_results?.overdue_count_gt_30d ?? 0}
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-md border border-gray-200">
                <p className="text-xs text-gray-500">Analyzed Batches</p>
                <p className="text-lg font-bold text-gray-900 mt-0.5">
                  {batchAnalytics.spark_or_fallback_results?.total_reports ?? 0}
                </p>
              </div>
            </div>

            {/* Spatial Clusters Table */}
            {batchAnalytics.spark_or_fallback_results?.top_spatial_clusters?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-2">High-Density Damage Clusters (~1.1 km Grid Resolution)</p>
                <div className="overflow-x-auto border border-gray-200 rounded-md">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 uppercase font-medium">
                      <tr>
                        <th className="py-2 px-3">Grid Centroid (Lat, Lon)</th>
                        <th className="py-2 px-3 text-right">Defect Count</th>
                        <th className="py-2 px-3 text-right">Avg Priority Score</th>
                        <th className="py-2 px-3 text-center">Density</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {batchAnalytics.spark_or_fallback_results.top_spatial_clusters.map((c: any, idx: number) => (
                        <tr key={idx} className="hover:bg-gray-50/50">
                          <td className="py-2 px-3 font-mono font-medium text-gray-900">
                            {c.grid_lat.toFixed(2)}°, {c.grid_lon.toFixed(2)}°
                          </td>
                          <td className="py-2 px-3 text-right font-semibold text-gray-800">
                            {c.damage_count}
                          </td>
                          <td className="py-2 px-3 text-right font-mono text-gray-700">
                            {c.avg_priority !== undefined ? `${c.avg_priority}/100` : '—'}
                          </td>
                          <td className="py-2 px-3 text-center">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                              c.damage_count >= 15
                                ? 'bg-red-50 text-red-700 border border-red-200'
                                : c.damage_count >= 6
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : 'bg-gray-100 text-gray-700'
                            }`}>
                              {c.damage_count >= 15 ? 'Critical Hotspot' : c.damage_count >= 6 ? 'Elevated' : 'Moderate'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
