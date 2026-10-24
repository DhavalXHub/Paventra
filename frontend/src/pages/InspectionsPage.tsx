import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Video, Upload, AlertTriangle, CheckCircle2, Clock, MapPin, RefreshCw, Layers, ShieldCheck, ChevronRight } from 'lucide-react';
import api from '../lib/api';
import type { InspectionJob, InspectionFrame } from '../types';
import { Card, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { Alert, EmptyState, Skeleton } from '../components/Feedback';
import { Input, Textarea } from '../components/FormElements';
import { formatDateTime } from '../lib/constants';

export default function InspectionsPage() {
  const qc = useQueryClient();
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Form states
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  const [gpsFile, setGpsFile] = useState<File | null>(null);
  const [sampleRate, setSampleRate] = useState('30');
  const [notes, setNotes] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  const mediaInputRef = useRef<HTMLInputElement>(null);
  const gpsInputRef = useRef<HTMLInputElement>(null);

  const { data: jobs, isLoading } = useQuery<InspectionJob[]>({
    queryKey: ['inspections'],
    queryFn: () => api.get('/inspections').then((r) => r.data),
    refetchInterval: 5000, // Poll active jobs
  });

  const { data: frames, isLoading: framesLoading } = useQuery<InspectionFrame[]>({
    queryKey: ['inspection-frames', selectedJobId],
    queryFn: () => api.get(`/inspections/${selectedJobId}/frames`).then((r) => r.data),
    enabled: !!selectedJobId,
  });

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!mediaFile) throw new Error('Video/Media file is required');
      const formData = new FormData();
      formData.append('media_file', mediaFile);
      if (gpsFile) formData.append('gps_track_file', gpsFile);
      formData.append('sample_rate', sampleRate || '30');
      if (notes) formData.append('notes', notes);

      return api.post('/inspections', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inspections'] });
      setFormSuccess('Inspection job queued successfully. Frame extraction and AI inference started in background.');
      setMediaFile(null);
      setGpsFile(null);
      setNotes('');
      setShowUploadForm(false);
    },
    onError: (err: { response?: { data?: { detail?: string } }; message?: string }) => {
      setFormError(err?.response?.data?.detail ?? err?.message ?? 'Failed to submit inspection job');
    },
  });

  const selectedJob = jobs?.find((j) => j.id === selectedJobId);

  return (
    <div className="p-6 max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Video className="w-5 h-5 text-accent" />
            Automatic Road Inspections (Method B)
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Prerecorded video & survey frame processing with synchronized GPS track linking and sequential deduplication.
          </p>
        </div>
        <Button
          onClick={() => {
            setShowUploadForm(!showUploadForm);
            setFormError(null);
            setFormSuccess(null);
          }}
          size="sm"
        >
          <Upload className="w-4 h-4 mr-1.5" />
          {showUploadForm ? 'Close upload form' : 'New inspection job'}
        </Button>
      </div>

      {formSuccess && <Alert type="success" message={formSuccess} />}
      {formError && <Alert type="error" message={formError} />}

      {/* Upload Form */}
      {showUploadForm && (
        <Card className="border-accent/40 bg-accent-light/10">
          <CardHeader>
            <CardTitle>Queue automated inspection job</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Media File */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Video or inspection media *
                </label>
                <input
                  ref={mediaInputRef}
                  type="file"
                  accept="video/*,image/*"
                  className="hidden"
                  onChange={(e) => setMediaFile(e.target.files?.[0] ?? null)}
                />
                <button
                  type="button"
                  onClick={() => mediaInputRef.current?.click()}
                  className="w-full flex items-center justify-center gap-2 px-3 py-3 border border-dashed border-gray-300 rounded-md bg-white hover:border-accent hover:bg-gray-50 text-xs text-gray-600 transition-colors"
                >
                  <Video className="w-4 h-4 text-gray-400" />
                  {mediaFile ? mediaFile.name : 'Choose video or frame archive (.mp4, .mov, etc.)'}
                </button>
              </div>

              {/* GPS Track File */}
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Synchronized GPS track (optional JSON)
                </label>
                <input
                  ref={gpsInputRef}
                  type="file"
                  accept=".json,.geojson"
                  className="hidden"
                  onChange={(e) => setGpsFile(e.target.files?.[0] ?? null)}
                />
                <button
                  type="button"
                  onClick={() => gpsInputRef.current?.click()}
                  className="w-full flex items-center justify-center gap-2 px-3 py-3 border border-dashed border-gray-300 rounded-md bg-white hover:border-accent hover:bg-gray-50 text-xs text-gray-600 transition-colors"
                >
                  <MapPin className="w-4 h-4 text-gray-400" />
                  {gpsFile ? gpsFile.name : 'Choose synchronized track file (.json)'}
                </button>
              </div>
            </div>

            {/* Safeguard Notice */}
            <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800">
              <ShieldCheck className="w-4 h-4 mt-0.5 text-amber-600 flex-shrink-0" />
              <div>
                <p className="font-semibold">Paventra Safeguards Enforced</p>
                <p className="text-amber-700 mt-0.5">
                  Exact GPS coordinates are NEVER guessed from pixels alone. If no synchronized GPS track file is provided,
                  observations will be marked with location source: <code>UNKNOWN</code> and require manual confirmation.
                  Duplicate observations across adjacent frames are suppressed within a 3-second temporal window.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Sample rate (frame step, e.g. 30 = 1 frame/sec at 30fps)"
                type="number"
                min="1"
                max="300"
                value={sampleRate}
                onChange={(e) => setSampleRate(e.target.value)}
              />
              <Input
                label="Job notes or road section reference"
                placeholder="e.g. Western Express Highway KM 12-18 Survey"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowUploadForm(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                loading={uploadMutation.isPending}
                disabled={!mediaFile}
                onClick={() => uploadMutation.mutate()}
              >
                Start automated inspection
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Jobs Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Jobs List */}
        <div className="lg:col-span-2 space-y-3">
          <Card padding={false}>
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-900">Inspection Jobs</h2>
              <span className="text-xs text-gray-500">{jobs?.length ?? 0} total</span>
            </div>

            {isLoading ? (
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 rounded-md" />
                ))}
              </div>
            ) : !jobs?.length ? (
              <EmptyState
                icon={<Video className="w-8 h-8" />}
                title="No inspection jobs"
                description="Upload a road survey video to start automatic damage inspection."
              />
            ) : (
              <div className="divide-y divide-gray-100">
                {jobs.map((j) => {
                  const isSelected = j.id === selectedJobId;
                  return (
                    <div
                      key={j.id}
                      onClick={() => setSelectedJobId(j.id)}
                      className={`p-4 cursor-pointer transition-colors ${
                        isSelected ? 'bg-accent-light/40 border-l-4 border-accent' : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-medium text-gray-900">
                              Job #{j.id.slice(0, 8)}
                            </span>
                            <span
                              className={`text-[11px] px-2 py-0.5 rounded font-medium ${
                                j.status === 'completed'
                                  ? 'bg-green-100 text-green-800'
                                  : j.status === 'processing'
                                  ? 'bg-blue-100 text-blue-800 animate-pulse'
                                  : j.status === 'failed'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-gray-100 text-gray-700'
                              }`}
                            >
                              {j.status.toUpperCase()}
                            </span>
                            {j.has_gps_track && (
                              <span className="text-[11px] bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-200">
                                GPS Synced
                              </span>
                            )}
                          </div>
                          {j.notes && (
                            <p className="text-xs text-gray-600 mt-1 font-medium">{j.notes}</p>
                          )}
                          <p className="text-[11px] text-gray-400 mt-0.5">
                            Created {formatDateTime(j.created_at)}
                          </p>
                        </div>

                        <div className="text-right text-xs">
                          <p className="font-semibold text-gray-900">
                            {j.reports_created} reports
                          </p>
                          <p className="text-gray-500">
                            {j.detections_count} detections
                          </p>
                        </div>
                      </div>

                      {/* Progress bar for running/completed jobs */}
                      <div className="mt-2.5">
                        <div className="flex justify-between text-[11px] text-gray-500 mb-1">
                          <span>Progress</span>
                          <span>{j.progress_percent.toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              j.status === 'failed'
                                ? 'bg-red-500'
                                : j.status === 'completed'
                                ? 'bg-green-600'
                                : 'bg-accent'
                            }`}
                            style={{ width: `${Math.max(3, j.progress_percent)}%` }}
                          />
                        </div>
                      </div>

                      {j.error_message && (
                        <p className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                          {j.error_message}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Frames / Details Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Job Details & Frames</CardTitle>
            </CardHeader>
            {!selectedJob ? (
              <p className="text-xs text-gray-500">
                Select an inspection job on the left to view extracted frames, model detections, and linked damage reports.
              </p>
            ) : (
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-2 bg-gray-50 p-3 rounded-md">
                  <div>
                    <span className="text-gray-500">Status</span>
                    <p className="font-semibold text-gray-900 uppercase">{selectedJob.status}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Frames Sampled</span>
                    <p className="font-semibold text-gray-900">
                      {selectedJob.total_frames_sampled ?? 'Processing…'}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500">Detections Found</span>
                    <p className="font-semibold text-gray-900">{selectedJob.detections_count}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Reports Created</span>
                    <p className="font-semibold text-emerald-600 font-bold">
                      {selectedJob.reports_created}
                    </p>
                  </div>
                </div>

                {framesLoading ? (
                  <div className="py-6 text-center text-gray-400">Loading frames…</div>
                ) : !frames?.length ? (
                  <p className="text-gray-500 py-3 text-center">
                    {selectedJob.status === 'processing'
                      ? 'Extracting and inferring frames…'
                      : 'No frames recorded for this job.'}
                  </p>
                ) : (
                  <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                    <p className="font-semibold text-gray-700">
                      Sampled Frames ({frames.length})
                    </p>
                    {frames.map((f) => (
                      <div
                        key={f.id}
                        className={`p-2.5 rounded border text-[11px] ${
                          f.is_duplicate
                            ? 'bg-gray-50 border-gray-200 opacity-60'
                            : f.report_id
                            ? 'bg-emerald-50 border-emerald-200'
                            : 'bg-white border-gray-200'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-medium text-gray-800">
                            Frame #{f.frame_index} (t={f.timestamp_seconds?.toFixed(1)}s)
                          </span>
                          {f.is_duplicate ? (
                            <span className="text-[10px] bg-gray-200 text-gray-600 px-1 rounded">
                              Deduplicated
                            </span>
                          ) : f.report_id ? (
                            <span className="text-[10px] bg-emerald-600 text-white px-1.5 py-0.5 rounded font-semibold">
                              Report Created
                            </span>
                          ) : null}
                        </div>

                        <div className="mt-1 text-gray-600 flex items-center gap-3">
                          <span>
                            Detections: <strong>{f.detections?.length ?? 0}</strong>
                          </span>
                          {f.confidence !== null && (
                            <span>
                              Max Conf: <strong>{(f.confidence * 100).toFixed(0)}%</strong>
                            </span>
                          )}
                          {f.latitude && f.longitude && (
                            <span className="font-mono text-gray-500">
                              {f.latitude.toFixed(4)}, {f.longitude.toFixed(4)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
