import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, MapPin } from 'lucide-react';
import api from '../lib/api';
import type { TrackResponse } from '../types';
import { formatDate, formatStatus } from '../lib/constants';
import { StatusBadge, SeverityBadge } from '../components/Badge';
import { Input } from '../components/FormElements';
import { Button } from '../components/Button';
import { Alert } from '../components/Feedback';

export default function TrackPage() {
  const [ref, setRef] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading, error, refetch } = useQuery<TrackResponse>({
    queryKey: ['track', search],
    queryFn: () => api.get(`/reports/track/${search}`).then((r) => r.data),
    enabled: !!search,
    retry: false,
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSearch(ref.trim().toUpperCase());
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-2">
        <div className="w-6 h-6 bg-accent rounded-md flex items-center justify-center">
          <MapPin className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="font-semibold text-gray-900 text-sm">Paventra</span>
        <div className="flex-1" />
        <a href="/report" className="text-xs text-accent hover:underline">New report</a>
      </header>

      <div className="max-w-lg mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Track your report</h1>
          <p className="text-sm text-gray-500 mt-0.5">Enter the reference number from your submission confirmation</p>
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            placeholder="e.g. PAV-AB12CD34"
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            className="flex-1 font-mono uppercase"
          />
          <Button type="submit" loading={isLoading} icon={<Search className="w-4 h-4" />}>
            Track
          </Button>
        </form>

        {error && (
          <Alert type="error" message="Report not found. Check your reference number and try again." />
        )}

        {data && (
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            <div className="p-5 border-b border-gray-100 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs text-gray-500">Reference</p>
                  <p className="font-mono font-bold text-lg text-gray-900">{data.public_ref}</p>
                </div>
                <StatusBadge status={data.status} />
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs text-gray-500">Damage type</p>
                  <p className="text-gray-900 capitalize">{data.damage_type.replace(/_/g, ' ')}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Severity</p>
                  <SeverityBadge severity={data.severity} />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Reported</p>
                  <p className="text-gray-900">{formatDate(data.created_at)}</p>
                </div>
                {data.resolved_at && (
                  <div>
                    <p className="text-xs text-gray-500">Resolved</p>
                    <p className="text-gray-900">{formatDate(data.resolved_at)}</p>
                  </div>
                )}
              </div>
              {data.review_reason && (
                <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
                  <p className="text-xs text-amber-700">Note from coordinator: {data.review_reason}</p>
                </div>
              )}
            </div>

            <div className="p-5">
              <p className="text-xs font-medium text-gray-500 mb-3">Status history</p>
              <div className="space-y-3">
                {data.history.map((h, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <div className="flex flex-col items-center">
                      <div className="w-2 h-2 rounded-full bg-accent mt-1.5" />
                      {i < data.history.length - 1 && <div className="w-px flex-1 bg-gray-200 my-1" />}
                    </div>
                    <div className="pb-2">
                      <div className="flex items-center gap-2">
                        <StatusBadge status={h.status} />
                        <span className="text-xs text-gray-400">{formatDate(h.changed_at)}</span>
                      </div>
                      {h.notes && <p className="text-xs text-gray-600 mt-1">{h.notes}</p>}
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
