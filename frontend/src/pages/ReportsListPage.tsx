import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, ChevronLeft, ChevronRight, Filter, RefreshCw, Sparkles, CheckCircle2, Clock, ArrowUpRight, ShieldAlert } from 'lucide-react';
import api from '../lib/api';
import type { ReportListResponse, ReportListItem } from '../types';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Skeleton, EmptyState, Alert } from '../components/Feedback';
import { Select } from '../components/FormElements';
import { Button } from '../components/Button';
import { formatDate, STATUS_OPTIONS, SEVERITY_OPTIONS, DAMAGE_TYPE_OPTIONS } from '../lib/constants';
import { FileText } from 'lucide-react';

const PAGE_SIZE = 20;

function PriorityPill({ score, label, assessmentStatus }: { score: number | null; label?: string | null; assessmentStatus?: string | null }) {
  if (score !== null) {
    const tier = label || (score >= 85 ? 'CRITICAL' : score >= 70 ? 'HIGH' : score >= 50 ? 'MEDIUM_HIGH' : score >= 25 ? 'MEDIUM' : 'LOW');
    const colorClasses =
      tier === 'CRITICAL'
        ? 'bg-red-100 text-red-800 border-red-200'
        : tier === 'HIGH'
        ? 'bg-orange-100 text-orange-800 border-orange-200'
        : tier === 'MEDIUM_HIGH'
        ? 'bg-amber-100 text-amber-800 border-amber-200'
        : tier === 'MEDIUM'
        ? 'bg-blue-100 text-blue-800 border-blue-200'
        : 'bg-gray-100 text-gray-700 border-gray-200';
    return (
      <div className="flex items-center gap-1.5">
        <span className="font-mono font-bold text-gray-900">{score.toFixed(0)}</span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold border ${colorClasses}`}>
          {tier.replace('_', ' ')}
        </span>
      </div>
    );
  }

  if (assessmentStatus === 'NO_IMAGE') {
    return <span className="text-[11px] text-gray-500 italic bg-gray-100 px-2 py-0.5 rounded">No image attached</span>;
  }
  if (assessmentStatus === 'NO_DETECTIONS') {
    return <span className="text-[11px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded">No distress found</span>;
  }
  return <span className="text-[11px] text-amber-600 bg-amber-50 px-2 py-0.5 rounded animate-pulse">Awaiting assessment</span>;
}

function AssessmentBadge({ status }: { status?: string | null }) {
  switch (status) {
    case 'COMPLETED':
      return <span className="text-[10px] bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded-full font-medium">Assessed (AI)</span>;
    case 'OVERRIDDEN':
      return <span className="text-[10px] bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full font-medium">Overridden (Human)</span>;
    case 'REVIEW_REQUIRED':
      return <span className="text-[10px] bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full font-medium">Review Required</span>;
    case 'NO_DETECTIONS':
      return <span className="text-[10px] bg-slate-100 text-slate-700 border border-slate-200 px-2 py-0.5 rounded-full font-medium">No Detections</span>;
    case 'NO_IMAGE':
      return <span className="text-[10px] bg-gray-100 text-gray-600 border border-gray-200 px-2 py-0.5 rounded-full font-medium">No Photo</span>;
    case 'FAILED':
      return <span className="text-[10px] bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded-full font-medium">Inference Failed</span>;
    default:
      return <span className="text-[10px] bg-yellow-50 text-yellow-700 border border-yellow-200 px-2 py-0.5 rounded-full font-medium">Pending</span>;
  }
}

export default function ReportsListPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [backfillMessage, setBackfillMessage] = useState<string | null>(null);

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

  const { data: recentReports } = useQuery<ReportListItem[]>({
    queryKey: ['reports', 'recent'],
    queryFn: () => api.get('/reports/recent?limit=4').then((r) => r.data),
    refetchInterval: 10000,
  });

  const backfillMutation = useMutation({
    mutationFn: () => api.post('/reports/backfill-assessments').then((r) => r.data),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['reports'] });
      setBackfillMessage(
        `Backfill completed: ${res.total_processed} processed (${res.assessed} assessed with YOLO/FIS, ${res.no_image} without images, ${res.no_detections} with no distress).`
      );
    },
  });

  const previewMutation = useMutation({
    mutationFn: () => api.post('/reports/backfill-assessments?dry_run=true').then((r) => r.data),
    onSuccess: (res) => {
      setBackfillMessage(res.message || `Preview: ${res.total_eligible} eligible records.`);
    },
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-semibold text-gray-900">Reports</h1>
          <p className="text-xs text-gray-500">
            {data?.total ?? 0} total reports · Actionable reports ordered by fuzzy priority score
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            loading={previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
          >
            Preview Backfill
          </Button>
          <Button
            variant="primary"
            size="sm"
            loading={backfillMutation.isPending}
            onClick={() => backfillMutation.mutate()}
          >
            <Sparkles className="w-3.5 h-3.5 mr-1.5 text-white" />
            Run Backfill
          </Button>
        </div>
      </div>

      {backfillMessage && (
        <Alert type="success" message={backfillMessage} />
      )}

      {/* ─── Recent Citizen Submissions Showcase ─── */}
      {recentReports && recentReports.length > 0 && (
        <div className="bg-gradient-to-r from-blue-50/70 via-indigo-50/50 to-slate-50 border border-blue-200/90 rounded-xl p-4 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-600"></span>
              </span>
              <h2 className="text-xs font-bold uppercase tracking-wider text-blue-950">
                Recent Citizen Submissions
              </h2>
              <span className="text-[11px] text-blue-700 bg-blue-100/80 px-2 py-0.5 rounded-full font-medium">
                Newest Incoming Reports
              </span>
            </div>
            <span className="text-[11px] text-blue-600 hidden sm:inline">
              Click any report to inspect or triage
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {recentReports.map((r) => (
              <div
                key={r.id}
                onClick={() => navigate(`/coordinator/reports/${r.id}`)}
                className="bg-white hover:bg-blue-50/50 border border-blue-100 hover:border-blue-300 rounded-lg p-3 shadow-xs transition-all cursor-pointer space-y-2 group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-gray-900 group-hover:text-blue-700">
                    {r.public_ref}
                  </span>
                  <StatusBadge status={r.status} />
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-900 capitalize truncate">
                    {r.damage_type.replace(/_/g, ' ')}
                  </p>
                  <p className="text-[11px] text-gray-500 truncate">
                    {r.address_hint || 'Coordinates reported'}
                  </p>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-gray-100 text-[11px]">
                  <AssessmentBadge status={r.assessment_status} />
                  <span className="text-gray-400 font-mono text-[10px]">
                    {formatDate(r.created_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-xs">
        <div className="px-4 py-3 border-b border-gray-200 bg-gray-50/80 flex items-center justify-between">
          <div>
            <h2 className="text-xs font-bold text-gray-800 uppercase tracking-wider">
              Actionable Priority Queue
            </h2>
            <p className="text-[11px] text-gray-500">
              Ranked automatically by Mamdani Soft Computing Fuzzy Priority Score (Highest first)
            </p>
          </div>
          <span className="text-xs font-mono font-medium text-gray-500">
            {data?.total ?? 0} total records
          </span>
        </div>
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
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Type (reported)</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Severity</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Priority Score & Tier</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">Assessment</th>
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
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <SeverityBadge severity={r.severity} />
                        {r.severity && (
                          <span className="text-[10px] text-gray-400 font-normal">
                            {r.severity_is_estimated ? '(AI)' : '(Verified)'}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <PriorityPill score={r.priority_score} label={r.priority_label} assessmentStatus={r.assessment_status} />
                    </td>
                    <td className="px-4 py-3">
                      <AssessmentBadge status={r.assessment_status} />
                    </td>
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
