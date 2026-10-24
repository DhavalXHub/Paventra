import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Wrench, MapPin, Calendar, Clock, CheckCircle2, Play, Upload, ExternalLink, LogOut, AlertCircle, FileText } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../features/auth/AuthContext';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card, CardHeader, CardTitle } from '../components/Card';
import { Alert, EmptyState, Skeleton } from '../components/Feedback';
import { Textarea } from '../components/FormElements';
import { formatDateTime, formatDate } from '../lib/constants';

interface RepairJob {
  assignment_id: string;
  report_id: string;
  public_ref: string;
  status: string;
  damage_type: string;
  severity: string | null;
  latitude: number | null;
  longitude: number | null;
  address_hint: string | null;
  description: string | null;
  team_id: string;
  team_name: string | null;
  target_date: string | null;
  assignment_notes: string | null;
  completion_notes: string | null;
  assigned_at: string;
  media_assets: Array<{
    id: string;
    file_name: string;
    asset_type: string;
    uploaded_at: string;
  }>;
}

export default function TeamJobsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [completionNotes, setCompletionNotes] = useState('');
  const [completionPhoto, setCompletionPhoto] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: jobs, isLoading } = useQuery<RepairJob[]>({
    queryKey: ['team-jobs'],
    queryFn: () => api.get('/teams/my-jobs').then((r) => r.data),
  });

  const startJobMutation = useMutation({
    mutationFn: (reportId: string) => api.patch(`/teams/jobs/${reportId}/start`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['team-jobs'] });
      setActionSuccess('Work marked as IN PROGRESS');
    },
    onError: (err: any) => {
      setActionError(err?.response?.data?.detail ?? 'Failed to update job status');
    },
  });

  const completionMutation = useMutation({
    mutationFn: (reportId: string) => {
      const form = new FormData();
      if (completionNotes) form.append('notes', completionNotes);
      if (completionPhoto) form.append('photo', completionPhoto);
      return api.post(`/reports/${reportId}/completion`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['team-jobs'] });
      setActionSuccess('Completion evidence submitted. The report is now Pending Coordinator Verification.');
      setActiveJobId(null);
      setCompletionNotes('');
      setCompletionPhoto(null);
    },
    onError: (err: any) => {
      setActionError(err?.response?.data?.detail ?? 'Failed to submit repair completion');
    },
  });

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Bar */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-accent rounded-md flex items-center justify-center">
            <Wrench className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-semibold text-gray-900 text-sm">Paventra</span>
            <span className="ml-2 text-xs bg-violet-50 text-violet-700 px-2 py-0.5 rounded border border-violet-200 font-medium">
              Repair Operations Portal
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-semibold text-gray-900">{user?.full_name}</p>
            <p className="text-[11px] text-gray-500">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-red-600 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Assigned Road Repair Work Orders</h1>
          <p className="text-xs text-gray-500 mt-1">
            Access assigned location evidence, mark on-site commencement, and submit completion photographs for coordinator verification.
          </p>
        </div>

        {actionSuccess && <Alert type="success" message={actionSuccess} />}
        {actionError && <Alert type="error" message={actionError} />}

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32 rounded-xl" />
            ))}
          </div>
        ) : !jobs?.length ? (
          <Card>
            <EmptyState
              icon={<Wrench className="w-10 h-10 text-gray-400" />}
              title="No active repair jobs assigned"
              description="Your team currently has no open road damage repair assignments."
            />
          </Card>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => {
              const primaryPhoto = job.media_assets?.find((m) => m.asset_type === 'report_photo') ?? job.media_assets?.[0];
              const photoUrl = primaryPhoto ? `/uploads/reports/${primaryPhoto.file_name}` : null;
              const isCompleting = activeJobId === job.report_id;

              return (
                <div
                  key={job.assignment_id}
                  className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:border-accent/40 transition-colors space-y-4"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-bold text-base text-gray-900">
                          {job.public_ref}
                        </span>
                        <StatusBadge status={job.status} />
                        {job.severity && <SeverityBadge severity={job.severity} />}
                        {job.team_name && (
                          <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded">
                            {job.team_name}
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-medium text-gray-800 capitalize">
                        {job.damage_type.replace(/_/g, ' ')}
                        {job.address_hint && (
                          <span className="font-normal text-gray-500"> · {job.address_hint}</span>
                        )}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      {job.target_date && (
                        <span className="flex items-center gap-1 text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200 font-medium">
                          <Calendar className="w-3.5 h-3.5" />
                          Target: {formatDate(job.target_date)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Evidence & Instructions */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-gray-100 text-xs">
                    {/* Photo thumbnail */}
                    {photoUrl && (
                      <div className="rounded-lg overflow-hidden border border-gray-200 bg-gray-50 h-36">
                        <img
                          src={photoUrl}
                          alt="Damage site"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    )}

                    {/* Details */}
                    <div className={`${photoUrl ? 'md:col-span-2' : 'md:col-span-3'} space-y-2`}>
                      {job.assignment_notes && (
                        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-900">
                          <span className="font-semibold">Coordinator instructions: </span>
                          {job.assignment_notes}
                        </div>
                      )}

                      {job.description && (
                        <p className="text-gray-600">
                          <span className="font-semibold text-gray-700">Citizen description: </span>
                          {job.description}
                        </p>
                      )}

                      {job.latitude && job.longitude && (
                        <div className="flex items-center gap-3 text-gray-500 pt-1">
                          <span className="font-mono">
                            GPS: {job.latitude.toFixed(5)}, {job.longitude.toFixed(5)}
                          </span>
                          <a
                            href={`https://www.google.com/maps?q=${job.latitude},${job.longitude}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-accent inline-flex items-center gap-1 font-medium hover:underline"
                          >
                            Open in Maps
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      )}

                      <p className="text-[11px] text-gray-400">
                        Assigned on {formatDateTime(job.assigned_at)}
                      </p>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-gray-100">
                    <div className="text-xs text-gray-500">
                      Current work status: <strong className="capitalize">{job.status.replace(/_/g, ' ')}</strong>
                    </div>

                    <div className="flex items-center gap-2">
                      {job.status === 'assigned' && (
                        <Button
                          size="sm"
                          loading={startJobMutation.isPending}
                          onClick={() => startJobMutation.mutate(job.report_id)}
                          icon={<Play className="w-3.5 h-3.5" />}
                        >
                          Start On-Site Work
                        </Button>
                      )}

                      {job.status === 'in_progress' && !isCompleting && (
                        <Button
                          size="sm"
                          onClick={() => {
                            setActiveJobId(job.report_id);
                            setActionSuccess(null);
                            setActionError(null);
                          }}
                          icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                        >
                          Submit Completion Evidence
                        </Button>
                      )}

                      {job.status === 'pending_verification' && (
                        <span className="text-xs bg-orange-50 text-orange-700 border border-orange-200 px-3 py-1.5 rounded-md font-medium flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          Pending Coordinator Verification
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Inline Completion Form */}
                  {isCompleting && (
                    <div className="p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-3 mt-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-gray-900">
                          Submit Repair Completion for {job.public_ref}
                        </span>
                        <button
                          onClick={() => setActiveJobId(null)}
                          className="text-xs text-gray-500 hover:text-gray-700"
                        >
                          Cancel
                        </button>
                      </div>

                      <Textarea
                        label="Work notes / Materials used"
                        value={completionNotes}
                        onChange={(e) => setCompletionNotes(e.target.value)}
                        placeholder="e.g. Cleared debris, laid hot-mix asphalt patch, compacted to grade."
                        rows={2}
                      />

                      <div>
                        <label className="block text-xs font-semibold text-gray-700 mb-1">
                          After-repair photograph (recommended)
                        </label>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={(e) => setCompletionPhoto(e.target.files?.[0] ?? null)}
                        />
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-dashed border-gray-300 rounded-md bg-white hover:border-accent text-xs text-gray-600 transition-colors"
                        >
                          <Upload className="w-3.5 h-3.5" />
                          {completionPhoto ? completionPhoto.name : 'Choose after-repair photo…'}
                        </button>
                      </div>

                      <div className="flex justify-end gap-2 pt-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setActiveJobId(null)}
                        >
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          loading={completionMutation.isPending}
                          onClick={() => completionMutation.mutate(job.report_id)}
                        >
                          Confirm & Submit to Coordinator
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
