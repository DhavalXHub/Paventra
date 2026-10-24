import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import api from '../lib/api';
import type { ReportListResponse } from '../types';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Skeleton, EmptyState } from '../components/Feedback';
import { Select } from '../components/FormElements';
import { formatDate, STATUS_OPTIONS, SEVERITY_OPTIONS, DAMAGE_TYPE_OPTIONS } from '../lib/constants';
import { FileText } from 'lucide-react';

const PAGE_SIZE = 20;

export default function ReportsListPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState('');

  const page = Number(params.get('page') ?? 1);
  const status = params.get('status') ?? '';
  const severity = params.get('severity') ?? '';
  const damage_type = params.get('damage_type') ?? '';

  const { data, isLoading } = useQuery<ReportListResponse>({
    queryKey: ['reports', page, status, severity, damage_type, search],
    queryFn: () => {
      const p = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
      if (status) p.append('status', status);
      if (severity) p.append('severity', severity);
      if (damage_type) p.append('damage_type', damage_type);
      if (search) p.append('search', search);
      return api.get(`/reports?${p}`).then((r) => r.data);
    },
    placeholderData: (prev) => prev,
  });

  function setFilter(key: string, val: string) {
    const next = new URLSearchParams(params);
    if (val) next.set(key, val);
    else next.delete(key);
    next.set('page', '1');
    setParams(next);
  }

  function setPage(p: number) {
    const next = new URLSearchParams(params);
    next.set('page', String(p));
    setParams(next);
  }

  return (
    <div className="p-6 space-y-4 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-gray-900">Reports</h1>
          <p className="text-xs text-gray-500">{data?.total ?? 0} total reports</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[180px]">
          <label className="block text-xs font-medium text-gray-700 mb-1">Search</label>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              className="w-full pl-8 pr-3 py-2 text-sm border border-gray-200 rounded-md
                focus:outline-none focus:ring-2 focus:ring-accent"
              placeholder="Reference or description…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && setFilter('page', '1')}
            />
          </div>
        </div>
        <div className="w-36">
          <Select
            label="Status"
            value={status}
            options={[{ value: '', label: 'All statuses' }, ...STATUS_OPTIONS]}
            onChange={(e) => setFilter('status', e.target.value)}
          />
        </div>
        <div className="w-32">
          <Select
            label="Severity"
            value={severity}
            options={[{ value: '', label: 'All severities' }, ...SEVERITY_OPTIONS]}
            onChange={(e) => setFilter('severity', e.target.value)}
          />
        </div>
        <div className="w-40">
          <Select
            label="Damage type"
            value={damage_type}
            options={[{ value: '', label: 'All types' }, ...DAMAGE_TYPE_OPTIONS]}
            onChange={(e) => setFilter('damage_type', e.target.value)}
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-10" />)}
          </div>
        ) : !data?.items.length ? (
          <EmptyState
            icon={<FileText className="w-10 h-10" />}
            title="No reports found"
            description="Try adjusting your filters"
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">Reference</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Severity</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Priority</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Source</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 whitespace-nowrap">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => navigate(`/coordinator/reports/${r.id}`)}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-gray-900">{r.public_ref}</td>
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3 text-gray-700 capitalize">{r.damage_type.replace(/_/g, ' ')}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={r.severity} /></td>
                    <td className="px-4 py-3">
                      {r.priority_score !== null ? (
                        <span className="font-medium text-gray-900">{r.priority_score.toFixed(0)}</span>
                      ) : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-3 capitalize text-gray-500">{r.source}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(r.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="border-t border-gray-100 px-4 py-3 flex items-center justify-between">
            <span className="text-xs text-gray-500">
              Page {data.page} of {data.pages} · {data.total} reports
            </span>
            <div className="flex gap-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= data.pages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
