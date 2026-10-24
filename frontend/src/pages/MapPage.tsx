import React from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../lib/api';
import type { MapMarker } from '../types';
import { ReportMap } from '../components/Map';
import { Skeleton } from '../components/Feedback';

export default function MapPage() {
  const { data: markers, isLoading } = useQuery<MapMarker[]>({
    queryKey: ['map-markers'],
    queryFn: () => api.get('/reports/map/markers').then((r) => r.data),
    refetchInterval: 60000,
  });

  return (
    <div className="p-6 space-y-4 max-w-7xl">
      <div>
        <h1 className="text-base font-semibold text-gray-900">Map view</h1>
        <p className="text-xs text-gray-500">
          {markers?.length ?? 0} reports with location data
        </p>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
        {isLoading ? (
          <Skeleton className="h-[560px]" />
        ) : (
          <ReportMap markers={markers ?? []} height="560px" />
        )}
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-gray-600">
        {[
          ['submitted', '#6b7280'],
          ['under_review', '#d97706'],
          ['verified', '#2563eb'],
          ['assigned', '#7c3aed'],
          ['in_progress', '#0891b2'],
          ['resolved', '#16a34a'],
          ['rejected', '#dc2626'],
        ].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            <span className="capitalize">{String(label).replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
