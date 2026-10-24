import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, Calendar, User, Cpu, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import api from '../lib/api';
import type { Report, Team } from '../types';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Button } from '../components/Button';
import { Alert } from '../components/Feedback';
import { Select, Textarea } from '../components/FormElements';
import { formatDateTime, formatRelative, NEXT_TRANSITIONS, STATUS_LABELS } from '../lib/constants';
import { Card, CardHeader, CardTitle } from '../components/Card';

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [actionStatus, setActionStatus] = useState('');
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [teamId, setTeamId] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const { data: report, isLoading } = useQuery<Report>({
    queryKey: ['report', id],
    queryFn: () => api.get(`/reports/${id}`).then((r) => r.data),
  });

  const { data: teams } = useQuery<Team[]>({
    queryKey: ['teams'],
    queryFn: () => api.get('/teams').then((r) => r.data),
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, reason, notes }: { status: string; reason?: string; notes?: string }) =>
      api.patch(`/reports/${id}/status`, { status, reason, notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['report', id] });
      qc.invalidateQueries({ queryKey: ['reports'] });
      setActionSuccess('Status updated successfully');
      setActionStatus('');
      setReason('');
      setNotes('');
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setActionError(err?.response?.data?.detail ?? 'Failed to update status');
    },
  });

  const assignMutation = useMutation({
    mutationFn: ({ team_id, target_date, notes }: { team_id: string; target_date?: string; notes?: string }) =>
      api.post(`/reports/${id}/assign`, {
        team_id,
        target_date: target_date || undefined,
        notes,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['report', id] });
      setActionSuccess('Team assigned successfully');
      setTeamId('');
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setActionError(err?.response?.data?.detail ?? 'Failed to assign team');
    },
  });

  if (isLoading) {
    return (
      <div className="p-6 flex items-center gap-2 text-gray-500">
        <Clock className="w-4 h-4 animate-spin" />
        Loading report…
      </div>
    );
  }
  if (!report) return <div className="p-6 text-gray-500">Report not found.</div>;

  const nextStatuses = NEXT_TRANSITIONS[report.status] ?? [];
  const mediaUrl = report.media_assets[0]
    ? `/uploads/reports/${report.media_assets[0].file_name}`
    : null;

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(-1)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-500">
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-base font-semibold text-gray-900 font-mono">{report.public_ref}</h1>
            <StatusBadge status={report.status} />
            {report.severity && <SeverityBadge severity={report.severity} />}
            {report.severity_is_estimated && (
              <span className="text-xs text-amber-600 border border-amber-200 bg-amber-50 px-1.5 py-0.5 rounded">
                AI-estimated
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {formatDateTime(report.created_at)} · {report.source} · {report.location_source}
          </p>
        </div>
      </div>

      {actionError && <Alert type="error" message={actionError} />}
      {actionSuccess && <Alert type="success" message={actionSuccess} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: evidence + details */}
        <div className="lg:col-span-2 space-y-4">
          {/* Photo */}
          {mediaUrl && (
            <Card padding={false} className="overflow-hidden">
              <img src={mediaUrl} alt="Damage evidence" className="w-full object-cover max-h-72" />
            </Card>
          )}

          {/* Details */}
          <Card>
            <CardHeader><CardTitle>Report details</CardTitle></CardHeader>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-500">Damage type</p>
                <p className="text-gray-900 capitalize font-medium">{report.damage_type.replace(/_/g, ' ')}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Source</p>
                <p className="text-gray-900 capitalize">{report.source}</p>
              </div>
              {report.latitude && (
                <div>
                  <p className="text-xs text-gray-500">Coordinates</p>
                  <p className="text-gray-900 font-mono text-xs">
                    {report.latitude.toFixed(5)}, {report.longitude?.toFixed(5)}
                  </p>
                </div>
              )}
              {report.address_hint && (
                <div className="col-span-2">
                  <p className="text-xs text-gray-500">Address</p>
                  <p className="text-gray-900">{report.address_hint}</p>
                </div>
              )}
              {report.description && (
                <div className="col-span-2">
                  <p className="text-xs text-gray-500">Description</p>
                  <p className="text-gray-700">{report.description}</p>
                </div>
              )}
            </div>
          </Card>

          {/* AI Assessment */}
          {(report.ai_confidence !== null || report.ai_damage_type) && (
            <Card>
              <CardHeader>
                <CardTitle>AI assessment</CardTitle>
                <span className="text-xs text-amber-600 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Estimated — not verified
                </span>
              </CardHeader>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-gray-500">Detected type</p>
                  <p className="font-medium text-gray-900 capitalize">{report.ai_damage_type ?? '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Confidence</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-gray-200 rounded-full">
                      <div
                        className="h-1.5 bg-accent rounded-full"
                        style={{ width: `${Math.round((report.ai_confidence ?? 0) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-gray-700">
                      {Math.round((report.ai_confidence ?? 0) * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Priority */}
          {report.priority_assessment && (
            <Card>
              <CardHeader>
                <CardTitle>Fuzzy priority assessment</CardTitle>
                <span className="font-bold text-lg text-gray-900">
                  {report.priority_assessment.priority_score.toFixed(0)}/100
                  <span className="ml-2 text-sm font-normal text-gray-500">
                    {report.priority_assessment.priority_label}
                  </span>
                </span>
              </CardHeader>
              <div className="space-y-2">
                {report.priority_assessment.top_contributing_factors.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      f.weight === 'strong' ? 'bg-red-500' : f.weight === 'medium' ? 'bg-amber-500' : 'bg-green-500'
                    }`} />
                    <span className="text-gray-700">{f.factor}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Status history */}
          <Card>
            <CardHeader><CardTitle>Status history</CardTitle></CardHeader>
            <div className="space-y-3">
              {report.status_history.map((h, i) => (
                <div key={i} className="flex gap-3 items-start text-xs">
                  <div className="w-2 h-2 rounded-full bg-accent mt-1.5 flex-shrink-0" />
                  <div>
                    <StatusBadge status={h.to_status} />
                    <span className="ml-2 text-gray-400">{formatDateTime(h.changed_at)}</span>
                    {h.changed_by_email && <span className="ml-2 text-gray-500">· {h.changed_by_email}</span>}
                    {h.reason && <p className="text-gray-600 mt-0.5">{h.reason}</p>}
                    {h.notes && <p className="text-gray-500 mt-0.5">{h.notes}</p>}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right: actions */}
        <div className="space-y-4">
          {/* Status action */}
          {nextStatuses.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Update status</CardTitle></CardHeader>
              <div className="space-y-3">
                <Select
                  label="New status"
                  value={actionStatus}
                  options={[
                    { value: '', label: 'Select…' },
                    ...nextStatuses.map((s) => ({ value: s, label: STATUS_LABELS[s] ?? s })),
                  ]}
                  onChange={(e) => { setActionStatus(e.target.value); setActionError(null); setActionSuccess(null); }}
                />
                {actionStatus === 'rejected' && (
                  <Textarea
                    label="Rejection reason *"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={2}
                    placeholder="Explain why this report is rejected"
                  />
                )}
                <Textarea
                  label="Notes (optional)"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Additional notes for the record"
                />
                <Button
                  className="w-full"
                  disabled={!actionStatus || (actionStatus === 'rejected' && !reason)}
                  loading={statusMutation.isPending}
                  onClick={() => statusMutation.mutate({ status: actionStatus, reason, notes })}
                >
                  Apply
                </Button>
              </div>
            </Card>
          )}

          {/* Assign team (when verified) */}
          {report.status === 'verified' && teams && (
            <Card>
              <CardHeader><CardTitle>Assign repair team</CardTitle></CardHeader>
              <div className="space-y-3">
                <Select
                  label="Team"
                  value={teamId}
                  options={[
                    { value: '', label: 'Select team…' },
                    ...teams.map((t) => ({ value: t.id, label: t.name })),
                  ]}
                  onChange={(e) => setTeamId(e.target.value)}
                />
                <div className="space-y-1">
                  <label className="block text-xs font-medium text-gray-700">Target date (optional)</label>
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-md
                      focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>
                <Button
                  className="w-full"
                  disabled={!teamId}
                  loading={assignMutation.isPending}
                  onClick={() => assignMutation.mutate({ team_id: teamId, target_date: targetDate || undefined })}
                >
                  Assign team
                </Button>
              </div>
            </Card>
          )}

          {/* Current assignment */}
          {report.assignment && (
            <Card>
              <CardHeader><CardTitle>Assignment</CardTitle></CardHeader>
              <div className="text-sm space-y-2">
                <div>
                  <p className="text-xs text-gray-500">Team</p>
                  <p className="font-medium text-gray-900">{report.assignment.team_name ?? report.assignment.team_id}</p>
                </div>
                {report.assignment.target_date && (
                  <div>
                    <p className="text-xs text-gray-500">Target date</p>
                    <p className="text-gray-900">{formatDateTime(report.assignment.target_date)}</p>
                  </div>
                )}
                {report.assignment.notes && (
                  <div>
                    <p className="text-xs text-gray-500">Notes</p>
                    <p className="text-gray-700">{report.assignment.notes}</p>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
