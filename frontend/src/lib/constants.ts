import type { ReportStatus, SeverityLevel, DamageType } from '../types';

export const STATUS_LABELS: Record<string, string> = {
  submitted: 'Submitted',
  under_review: 'Under Review',
  verified: 'Verified',
  assigned: 'Assigned',
  in_progress: 'In Progress',
  pending_verification: 'Pending Verification',
  resolved: 'Resolved',
  rejected: 'Rejected',
};

export const STATUS_COLORS: Record<string, string> = {
  submitted: 'bg-gray-100 text-gray-700 border-gray-200',
  under_review: 'bg-amber-50 text-amber-700 border-amber-200',
  verified: 'bg-blue-50 text-blue-700 border-blue-200',
  assigned: 'bg-violet-50 text-violet-700 border-violet-200',
  in_progress: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  pending_verification: 'bg-orange-50 text-orange-700 border-orange-200',
  resolved: 'bg-green-50 text-green-700 border-green-200',
  rejected: 'bg-red-50 text-red-700 border-red-200',
};

export const SEVERITY_COLORS: Record<string, string> = {
  low: 'bg-green-50 text-green-700 border-green-200',
  moderate: 'bg-amber-50 text-amber-700 border-amber-200',
  high: 'bg-orange-50 text-orange-700 border-orange-200',
  critical: 'bg-red-50 text-red-700 border-red-200',
};

export const SEVERITY_DOT_COLORS: Record<string, string> = {
  low: 'bg-green-500',
  moderate: 'bg-amber-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

export const MAP_MARKER_COLORS: Record<string, string> = {
  submitted: '#6b7280',
  under_review: '#d97706',
  verified: '#2563eb',
  assigned: '#7c3aed',
  in_progress: '#0891b2',
  pending_verification: '#ea580c',
  resolved: '#16a34a',
  rejected: '#dc2626',
};

export function formatStatus(s: string) {
  return STATUS_LABELS[s] ?? s;
}

export function formatDamageType(d: string) {
  return d.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatRelative(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export const DAMAGE_TYPE_OPTIONS: { value: DamageType; label: string }[] = [
  { value: 'pothole', label: 'Pothole' },
  { value: 'crack', label: 'Crack' },
  { value: 'surface_deterioration', label: 'Surface Deterioration' },
  { value: 'rutting', label: 'Rutting' },
  { value: 'edge_break', label: 'Edge Break' },
  { value: 'other', label: 'Other' },
  { value: 'unknown', label: 'Not sure' },
];

export const STATUS_OPTIONS = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }));
export const SEVERITY_OPTIONS: { value: SeverityLevel; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
];

// Valid next transitions for coordinator UI
export const NEXT_TRANSITIONS: Record<string, string[]> = {
  submitted: ['under_review', 'rejected'],
  under_review: ['verified', 'rejected'],
  verified: ['assigned', 'rejected'],
  assigned: ['in_progress', 'rejected'],
  in_progress: ['pending_verification'],
  pending_verification: ['resolved', 'in_progress'],
  rejected: ['under_review'],
  resolved: [],
};
