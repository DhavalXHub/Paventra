import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Search, MapPin, Upload, PlusCircle } from 'lucide-react';
import api from '../lib/api';
import type { TrackResponse } from '../types';
import { formatDate, formatDateTime } from '../lib/constants';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Input, Textarea } from '../components/FormElements';
import { Button } from '../components/Button';
import { Alert } from '../components/Feedback';

export default function TrackPage() {
  const { ref: paramRef } = useParams<{ ref?: string }>();
  const [ref, setRef] = useState(paramRef ?? '');
  const [search, setSearch] = useState(paramRef ?? '');

  // Additional evidence form
  const [showEvidenceForm, setShowEvidenceForm] = useState(false);
  const [evidenceNotes, setEvidenceNotes] = useState('');
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceSuccess, setEvidenceSuccess] = useState<string | null>(null);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (paramRef) {
      setRef(paramRef.toUpperCase());
      setSearch(paramRef.toUpperCase());
    }
  }, [paramRef]);

  const { data, isLoading, error, refetch } = useQuery<TrackResponse>({
    queryKey: ['track', search],
    queryFn: () => api.get(`/reports/track/${search}`).then((r) => r.data),
    enabled: !!search,
    retry: false,
  });

  const evidenceMutation = useMutation({
    mutationFn: () => {
      const form = new FormData();
      if (evidenceNotes) form.append('notes', evidenceNotes);
      if (evidenceFile) form.append('image', evidenceFile);
      return api.post(`/reports/track/${search}/evidence`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    onSuccess: () => {
      setEvidenceSuccess('Additional evidence attached successfully. The coordinator will review it.');
      setEvidenceNotes('');
      setEvidenceFile(null);
      setShowEvidenceForm(false);
      refetch();
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setEvidenceError(err?.response?.data?.detail ?? 'Failed to submit additional evidence');
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = ref.trim().toUpperCase();
    if (clean) {
      setSearch(clean);
      setEvidenceSuccess(null);
      setEvidenceError(null);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-2">
        <div className="w-6 h-6 bg-accent rounded-md flex items-center justify-center">
          <MapPin className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="font-semibold text-gray-900 text-sm">Paventra</span>
        <div className="flex-1" />
        <Link to="/report" className="text-xs text-accent hover:underline font-medium">
          New report
        </Link>
      </header>

      <div className="max-w-xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Track road report</h1>
          <p className="text-xs text-gray-500 mt-1">
            Enter the unique reference code (e.g. <code>PAV-XXXXXXXX</code>) from your submission.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            placeholder="e.g. PAV-AB12CD34"
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            className="flex-1 font-mono uppercase text-sm"
          />
          <Button type="submit" loading={isLoading} icon={<Search className="w-4 h-4" />}>
            Track
          </Button>
        </form>

        {error && (
          <Alert type="error" message="Report not found. Please verify the reference code and try again." />
        )}

        {data && (
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden space-y-0">
            <div className="p-5 border-b border-gray-100 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-500">Reference</p>
                  <p className="font-mono font-bold text-lg text-gray-900">{data.public_ref}</p>
                </div>
                <StatusBadge status={data.status} />
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-gray-500">Damage type</p>
                  <p className="text-gray-900 capitalize font-medium">{data.damage_type.replace(/_/g, ' ')}</p>
                </div>
                <div>
                  <p className="text-gray-500">Estimated severity</p>
                  <SeverityBadge severity={data.severity} />
                </div>
                <div>
                  <p className="text-gray-500">Reported</p>
                  <p className="text-gray-900">{formatDate(data.created_at)}</p>
                </div>
                {data.resolved_at && (
                  <div>
                    <p className="text-gray-500">Resolved</p>
                    <p className="text-emerald-600 font-semibold">{formatDate(data.resolved_at)}</p>
                  </div>
                )}
              </div>
              {data.review_reason && (
                <div className="bg-amber-50 border border-amber-200 rounded-md p-3 text-xs text-amber-800">
                  <span className="font-semibold">Coordinator note: </span>
                  {data.review_reason}
                </div>
              )}
            </div>

            {/* Additional Evidence Action (if not resolved) */}
            {data.status !== 'resolved' && data.status !== 'rejected' && (
              <div className="p-4 bg-gray-50 border-b border-gray-100">
                {evidenceSuccess && <Alert type="success" message={evidenceSuccess} className="mb-3" />}
                {evidenceError && <Alert type="error" message={evidenceError} className="mb-3" />}

                {!showEvidenceForm ? (
                  <button
                    onClick={() => setShowEvidenceForm(true)}
                    className="flex items-center gap-1.5 text-xs text-accent font-medium hover:underline"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    Provide additional evidence or details
                  </button>
                ) : (
                  <div className="space-y-3 bg-white p-3.5 rounded-lg border border-gray-200">
                    <p className="text-xs font-semibold text-gray-900">Add supplemental evidence</p>
                    <Textarea
                      label="Additional notes"
                      value={evidenceNotes}
                      onChange={(e) => setEvidenceNotes(e.target.value)}
                      rows={2}
                      placeholder="Add any landmark clarification, worsening condition, etc."
                    />
                    <div>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={(e) => setEvidenceFile(e.target.files?.[0] ?? null)}
                      />
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 border border-dashed border-gray-300 rounded-md hover:border-accent text-xs text-gray-600"
                      >
                        <Upload className="w-3.5 h-3.5" />
                        {evidenceFile ? evidenceFile.name : 'Attach additional photo'}
                      </button>
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setShowEvidenceForm(false)}
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        loading={evidenceMutation.isPending}
                        disabled={!evidenceNotes && !evidenceFile}
                        onClick={() => evidenceMutation.mutate()}
                      >
                        Submit evidence
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Status Timeline */}
            <div className="p-5">
              <p className="text-xs font-semibold text-gray-700 mb-3">Status timeline</p>
              <div className="space-y-3">
                {data.history.map((h, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-2 h-2 rounded-full bg-accent mt-1.5" />
                      {i < data.history.length - 1 && <div className="w-px flex-1 bg-gray-200 my-1 min-h-[20px]" />}
                    </div>
                    <div className="pb-1 text-xs">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={h.status} />
                        <span className="text-gray-400">{formatDateTime(h.changed_at)}</span>
                      </div>
                      {h.notes && <p className="text-gray-600 mt-1">{h.notes}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
