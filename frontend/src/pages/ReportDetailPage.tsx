import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, Link2, AlertTriangle, Clock, ShieldCheck, FileText, Image as ImageIcon } from 'lucide-react';
import api from '../lib/api';
import type { Report, Team, AuditEvent } from '../types';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Button } from '../components/Button';
import { Alert } from '../components/Feedback';
import { Select, Textarea } from '../components/FormElements';
import { formatDateTime, NEXT_TRANSITIONS, STATUS_LABELS } from '../lib/constants';
import { Card, CardHeader, CardTitle } from '../components/Card';
import { resolveAssetUrl } from '../lib/assets';

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
  const [completionNotes, setCompletionNotes] = useState('');
  const [completionPhoto, setCompletionPhoto] = useState<File | null>(null);
  const completionFileRef = useRef<HTMLInputElement>(null);
  const [showDuplicates, setShowDuplicates] = useState(false);

  // Human Override State
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideSeverity, setOverrideSeverity] = useState<string>('moderate');
  const [overrideDamageType, setOverrideDamageType] = useState<string>('');
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [overrideNotes, setOverrideNotes] = useState<string>('');

  const { data: report, isLoading } = useQuery<Report>({
    queryKey: ['report', id],
    queryFn: () => api.get(`/reports/${id}`).then((r) => r.data),
  });

  const { data: teams } = useQuery<Team[]>({
    queryKey: ['teams'],
    queryFn: () => api.get('/teams').then((r) => r.data),
  });

  const { data: auditEvents } = useQuery<AuditEvent[]>({
    queryKey: ['audit', id],
    queryFn: () => api.get(`/audit/${id}`).then((r) => r.data),
    enabled: !!id,
  });

  interface DuplicateCandidate {
    id: string;
    public_ref: string;
    distance_meters: number | null;
    similarity_score: number;
    same_damage_type: boolean;
    time_diff_days: number;
    distinction_category?: string;
    recommendation?: string;
    reasoning?: string;
  }

  const { data: duplicates, isFetching: dupesFetching } = useQuery<DuplicateCandidate[]>({
    queryKey: ['report-duplicates', id],
    queryFn: () => api.get(`/reports/${id}/duplicates`).then((r) => r.data),
    enabled: showDuplicates,
    staleTime: 60000,
  });

  const completionMutation = useMutation({
    mutationFn: ({ notes, photo }: { notes: string; photo: File | null }) => {
      const form = new FormData();
      if (notes) form.append('notes', notes);
      if (photo) form.append('photo', photo);
      return api.post(`/reports/${id}/completion`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['report', id] });
      setActionSuccess('Completion evidence submitted — report moved to Pending Verification');
      setCompletionNotes('');
      setCompletionPhoto(null);
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setActionError(err?.response?.data?.detail ?? 'Failed to submit completion');
    },
  });

  const linkDupeMutation = useMutation({
    mutationFn: (duplicateId: string) =>
      api.post(`/reports/${id}/duplicates/link`, { duplicate_id: duplicateId }),
    onSuccess: () => {
      setActionSuccess('Duplicate linked successfully');
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setActionError(err?.response?.data?.detail ?? 'Failed to link duplicate');
    },
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

  const overrideMutation = useMutation({
    mutationFn: ({ severity, damage_type, reason, notes }: { severity: string; damage_type?: string; reason: string; notes?: string }) =>
      api.post(`/reports/${id}/override`, { severity, damage_type: damage_type || undefined, reason, notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['report', id] });
      qc.invalidateQueries({ queryKey: ['reports'] });
      qc.invalidateQueries({ queryKey: ['audit', id] });
      setActionSuccess('Assessment override recorded successfully with audit trail.');
      setShowOverrideModal(false);
      setOverrideReason('');
      setOverrideNotes('');
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setActionError(err?.response?.data?.detail ?? 'Failed to override assessment');
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
          {/* Media Evidence Gallery */}
          {report.media_assets?.length > 0 && (
            <Card padding={false} className="overflow-hidden">
              <div className="p-3 border-b border-gray-100 flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-800 flex items-center gap-1.5">
                  <ImageIcon className="w-3.5 h-3.5 text-accent" />
                  Visual Evidence ({report.media_assets.length})
                </span>
              </div>
              <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                {report.media_assets.map((asset) => {
                  const url = resolveAssetUrl(
                    asset.file_path && (asset.file_path.startsWith('http://') || asset.file_path.startsWith('https://'))
                      ? asset.file_path
                      : asset.file_name,
                    asset.asset_type === 'completion_photo' ? 'completions' : 'reports'
                  );

                  const label =
                    asset.asset_type === 'completion_photo'
                      ? 'After-Repair Evidence'
                      : asset.asset_type === 'additional_evidence'
                      ? 'Citizen Additional Evidence'
                      : 'Initial Report Photo';

                  return (
                    <div key={asset.id} className="relative rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
                      <img src={url} alt={label} className="w-full h-44 object-cover" />
                      <div className="p-2 flex items-center justify-between text-[11px] bg-white border-t border-gray-100">
                        <span className="font-medium text-gray-700">{label}</span>
                        <span className="text-gray-400">{formatDateTime(asset.uploaded_at)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
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

          {/* AI Assessment & Prioritization */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between w-full">
                <CardTitle>Automatic Assessment & Prioritization</CardTitle>
                <div className="flex items-center gap-2">
                  {report.assessment_status === 'OVERRIDDEN' ? (
                    <span className="text-[11px] bg-purple-100 text-purple-800 font-semibold px-2 py-0.5 rounded border border-purple-200">
                      Human Overridden
                    </span>
                  ) : report.assessment_status === 'COMPLETED' ? (
                    <span className="text-[11px] bg-green-100 text-green-800 font-semibold px-2 py-0.5 rounded border border-green-200">
                      AI Assessed
                    </span>
                  ) : report.assessment_status === 'REVIEW_REQUIRED' ? (
                    <span className="text-[11px] bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded border border-amber-200">
                      Review Required
                    </span>
                  ) : report.assessment_status === 'NO_DETECTIONS' ? (
                    <span className="text-[11px] bg-slate-100 text-slate-800 font-semibold px-2 py-0.5 rounded border border-slate-200">
                      No Distress Detected
                    </span>
                  ) : report.assessment_status === 'NO_IMAGE' ? (
                    <span className="text-[11px] bg-gray-100 text-gray-700 font-semibold px-2 py-0.5 rounded border border-gray-200">
                      No Photo Available
                    </span>
                  ) : (
                    <span className="text-[11px] bg-yellow-100 text-yellow-800 font-semibold px-2 py-0.5 rounded border border-yellow-200">
                      Pending Assessment
                    </span>
                  )}
                  {report.ai_inference_ms && (
                    <span className="text-[11px] text-gray-500 font-mono bg-gray-100 px-1.5 py-0.5 rounded">
                      {Math.round(report.ai_inference_ms)}ms
                    </span>
                  )}
                </div>
              </div>
            </CardHeader>

            <div className="space-y-4 text-sm">
              {/* Human Override Banner if active */}
              {report.assessment_status === 'OVERRIDDEN' && (
                <div className="p-3 bg-purple-50 border border-purple-200 rounded-md text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-purple-900">Coordinator Human Override Applied</span>
                    {report.override_at && (
                      <span className="text-purple-600 text-[11px]">{formatDateTime(report.override_at)}</span>
                    )}
                  </div>
                  <p className="text-purple-800">
                    <strong>Reason:</strong> {report.override_reason}
                  </p>
                  <p className="text-purple-600 text-[11px]">
                    Original AI assessment: Severity {report.original_severity ?? '—'} · Priority Score {report.original_priority_score?.toFixed(0) ?? '—'}
                  </p>
                </div>
              )}

              {/* Notice for No Image or No Detections */}
              {report.assessment_status === 'NO_IMAGE' && (
                <div className="p-3 bg-gray-50 border border-gray-200 rounded-md text-xs text-gray-600">
                  <p className="font-semibold text-gray-800">No Photo Attached</p>
                  <p className="mt-0.5">This report was submitted without an image. Computer vision severity estimation is unavailable. Assessment requires physical coordinator review.</p>
                </div>
              )}

              {report.assessment_status === 'NO_DETECTIONS' && (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-700">
                  <p className="font-semibold text-slate-900">No Road Distress Detected</p>
                  <p className="mt-0.5">The YOLO model processed the photo but found no defects meeting the confidence threshold (&ge; 0.40). Coordinator review is required.</p>
                </div>
              )}

              {/* Model & Severity Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 p-3 rounded-md text-xs">
                <div>
                  <p className="text-gray-500">Reported Category</p>
                  <p className="font-semibold text-gray-900 capitalize mt-0.5">{report.damage_type.replace(/_/g, ' ')}</p>
                  <p className="text-[10px] text-blue-600 font-medium">(citizen reported)</p>
                </div>
                <div>
                  <p className="text-gray-500">AI Assessment</p>
                  {report.ai_damage_type && report.assessment_status !== 'NO_DETECTIONS' ? (
                    <div className="mt-0.5">
                      <p className="font-semibold text-gray-900 capitalize">{report.ai_damage_type.replace(/_/g, ' ')}</p>
                      <p className="text-[10px] text-green-600 font-medium">
                        {report.ai_confidence !== null ? `${Math.round(report.ai_confidence * 100)}% conf.` : '(AI detected)'}
                      </p>
                    </div>
                  ) : report.assessment_status === 'NO_DETECTIONS' ? (
                    <div className="mt-0.5">
                      <p className="font-semibold text-slate-800">No qualifying detection</p>
                      <p className="text-[10px] text-slate-500 font-medium">(&lt; 35% threshold)</p>
                    </div>
                  ) : (
                    <div className="mt-0.5">
                      <p className="font-semibold text-amber-700">Pending review</p>
                      <p className="text-[10px] text-amber-600">Awaiting inference</p>
                    </div>
                  )}
                </div>
                <div>
                  <p className="text-gray-500">Severity Assessment</p>
                  <div className="mt-0.5">
                    {report.severity ? (
                      <div className="flex items-center gap-1">
                        <SeverityBadge severity={report.severity} />
                        <span className="text-[10px] text-gray-400">
                          {report.severity_is_estimated ? '(AI)' : '(Verified)'}
                        </span>
                      </div>
                    ) : (
                      <div>
                        <p className="font-medium text-amber-700">Pending review</p>
                        <p className="text-[10px] text-gray-400">Requires verification</p>
                      </div>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-gray-500">Priority Score</p>
                  <div className="mt-0.5">
                    {report.priority_score !== null ? (
                      <p className="font-semibold text-accent text-sm">
                        {report.priority_score.toFixed(0)}/100
                      </p>
                    ) : (
                      <div>
                        <p className="font-medium text-gray-600">Pending required inputs</p>
                        <p className="text-[10px] text-gray-400">Awaiting verified severity</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* 2D Geometric Evidence breakdown */}
              {report.ai_bounding_boxes?.severity_estimation && (
                <div className="p-2.5 bg-white border border-gray-200 rounded-md text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-gray-800">
                      Measurable 2D Geometry Evidence:
                    </span>
                    <span className="text-[11px] text-gray-500">
                      Score: {report.ai_bounding_boxes.severity_estimation.score}/10
                    </span>
                  </div>
                  {report.ai_bounding_boxes.severity_estimation.features && (
                    <div className="grid grid-cols-2 gap-2 text-gray-600 text-[11px] pt-1">
                      <div>
                        Footprint area:{' '}
                        <span className="font-mono font-medium text-gray-900">
                          {report.ai_bounding_boxes.severity_estimation.features.visible_area_percent}%
                        </span>
                      </div>
                      <div>
                        Elongation:{' '}
                        <span className="font-mono font-medium text-gray-900">
                          {report.ai_bounding_boxes.severity_estimation.features.max_aspect_ratio}x
                        </span>
                      </div>
                    </div>
                  )}
                  <p className="text-[10px] text-gray-400 italic pt-1 border-t border-gray-200">
                    Method: 2D visible area & distress geometry. True structural cavity depth cannot be determined from optical imagery.
                  </p>
                </div>
              )}

              {/* Override Action Button */}
              <div className="pt-1">
                {!showOverrideModal ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setShowOverrideModal(true);
                      setOverrideSeverity(report.severity ?? 'moderate');
                      setOverrideDamageType(report.damage_type ?? 'pothole');
                    }}
                  >
                    Human Override / Correction
                  </Button>
                ) : (
                  <div className="p-4 bg-purple-50/50 border border-purple-200 rounded-lg space-y-3">
                    <h4 className="text-xs font-bold text-purple-900">Record Coordinator Assessment Override</h4>
                    <p className="text-[11px] text-purple-700">
                      Overrides must have an auditable justification. The original AI scores remain preserved for transparency.
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <Select
                        label="Corrected Severity"
                        value={overrideSeverity}
                        options={[
                          { value: 'low', label: 'Low — minor defect' },
                          { value: 'moderate', label: 'Moderate — standard repair' },
                          { value: 'high', label: 'High — safety concern' },
                          { value: 'critical', label: 'Critical — immediate hazard' },
                        ]}
                        onChange={(e) => setOverrideSeverity(e.target.value)}
                      />
                      <Select
                        label="Corrected Damage Type"
                        value={overrideDamageType}
                        options={[
                          { value: 'pothole', label: 'Pothole' },
                          { value: 'crack', label: 'Crack' },
                          { value: 'surface_deterioration', label: 'Surface Deterioration' },
                          { value: 'rutting', label: 'Rutting' },
                          { value: 'other', label: 'Other' },
                        ]}
                        onChange={(e) => setOverrideDamageType(e.target.value)}
                      />
                    </div>
                    <Textarea
                      label="Mandatory Reason for Override *"
                      value={overrideReason}
                      onChange={(e) => setOverrideReason(e.target.value)}
                      rows={2}
                      placeholder="e.g. Field inspection reveals deep sub-base cavitation posing two-wheeler tipping hazard."
                    />
                    <div className="flex gap-2 justify-end">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setShowOverrideModal(false)}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        disabled={!overrideReason || overrideReason.length < 5}
                        loading={overrideMutation.isPending}
                        onClick={() => overrideMutation.mutate({
                          severity: overrideSeverity,
                          damage_type: overrideDamageType,
                          reason: overrideReason,
                        })}
                      >
                        Save Human Override
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Priority */}
          {report.priority_assessment && (
            <Card>
              <CardHeader>
                <CardTitle>Mamdani Fuzzy Priority Assessment</CardTitle>
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

          {/* Audit trail */}
          {auditEvents && auditEvents.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-accent" />
                  Audit Trail
                </CardTitle>
              </CardHeader>
              <div className="space-y-2.5">
                {auditEvents.map((ev) => (
                  <div key={ev.id} className="p-2.5 bg-gray-50 rounded-md border border-gray-100 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-800 uppercase tracking-wider text-[10px] bg-white px-1.5 py-0.5 rounded border border-gray-200">
                        {ev.action.replace(/_/g, ' ')}
                      </span>
                      <span className="text-[11px] text-gray-400">{formatDateTime(ev.created_at)}</span>
                    </div>
                    {ev.actor_email && (
                      <p className="text-gray-500 text-[11px]">Actor: {ev.actor_email}</p>
                    )}
                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <div className="text-[11px] text-gray-600 font-mono bg-white p-1.5 rounded border border-gray-100 mt-1 overflow-x-auto">
                        {JSON.stringify(ev.details)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
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
                  onClick={() => statusMutation.mutate({
                    status: actionStatus,
                    reason,
                    notes,
                  })}
                >
                  Apply
                </Button>
              </div>
            </Card>
          )}

          {/* Assign or reassign team */}
          {(report.status === 'verified' || report.status === 'assigned') && teams && (
            <Card>
              <CardHeader>
                <CardTitle>{report.status === 'assigned' ? 'Reassign repair team' : 'Assign repair team'}</CardTitle>
              </CardHeader>
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
                  {report.status === 'assigned' ? 'Reassign team' : 'Assign team'}
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

          {/* Completion evidence upload (in-progress/assigned) */}
          {(report.status === 'in_progress' || report.status === 'assigned') && (
            <Card>
              <CardHeader>
                <CardTitle>Submit completion</CardTitle>
              </CardHeader>
              <div className="space-y-3">
                <p className="text-xs text-gray-500">
                  Upload evidence that work is complete. This moves the report to Pending Verification.
                </p>
                <Textarea
                  label="Completion notes"
                  value={completionNotes}
                  onChange={(e) => setCompletionNotes(e.target.value)}
                  rows={2}
                  placeholder="Describe what was done"
                />
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    After-repair photo (required)
                  </label>
                  <input
                    ref={completionFileRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => setCompletionPhoto(e.target.files?.[0] ?? null)}
                  />
                  <button
                    onClick={() => completionFileRef.current?.click()}
                    className="flex items-center gap-2 px-3 py-2 text-xs border border-dashed border-gray-300
                      rounded-md text-gray-500 hover:border-accent hover:text-accent transition-colors w-full"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    {completionPhoto ? completionPhoto.name : 'Choose photo…'}
                  </button>
                </div>
                <Button
                  className="w-full"
                  disabled={!completionPhoto}
                  loading={completionMutation.isPending}
                  onClick={() => completionMutation.mutate({ notes: completionNotes, photo: completionPhoto })}
                >
                  Submit completion
                </Button>
              </div>
            </Card>
          )}

          {/* Duplicate candidate review */}
          <Card>
            <CardHeader>
              <CardTitle>Duplicate check</CardTitle>
              <button
                onClick={() => setShowDuplicates((v) => !v)}
                className="text-xs text-accent hover:underline"
              >
                {showDuplicates ? 'Hide' : 'Check duplicates'}
              </button>
            </CardHeader>
            {showDuplicates && (
              <div className="mt-2">
                {dupesFetching ? (
                  <p className="text-xs text-gray-400">Searching…</p>
                ) : !duplicates?.length ? (
                  <p className="text-xs text-gray-500">No likely duplicates found nearby.</p>
                ) : (
                  <ul className="space-y-2">
                    {duplicates.map((d) => (
                      <li key={d.id} className="p-2.5 bg-gray-50 border border-gray-200 rounded-md text-xs space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-semibold text-gray-900">{d.public_ref}</span>
                          <span className="font-mono font-medium text-accent">{Math.round(d.similarity_score * 100)}% match</span>
                        </div>
                        {d.distinction_category && (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                              {d.distinction_category.replace(/_/g, ' ')}
                            </span>
                            {d.recommendation && (
                              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                d.recommendation === 'keep_separate'
                                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                  : d.recommendation === 'auto_link'
                                  ? 'bg-green-50 text-green-700 border border-green-200'
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {d.recommendation.replace(/_/g, ' ')}
                              </span>
                            )}
                          </div>
                        )}
                        <div className="text-gray-500 space-x-3 text-[11px]">
                          {d.distance_meters !== null && <span>{Math.round(d.distance_meters)}m away</span>}
                          <span>{d.time_diff_days.toFixed(0)}d apart</span>
                          {d.same_damage_type && <span className="text-gray-700">Same damage type</span>}
                        </div>
                        {d.reasoning && (
                          <p className="text-[11px] text-gray-600 italic">
                            {d.reasoning}
                          </p>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={linkDupeMutation.isPending}
                          onClick={() => linkDupeMutation.mutate(d.id)}
                          className="!text-xs !py-0.5 mt-1 border border-gray-200"
                        >
                          <Link2 className="w-3 h-3 mr-1" />
                          Mark as duplicate
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
