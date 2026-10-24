import React from 'react';
import { STATUS_COLORS, SEVERITY_COLORS, formatStatus } from '../lib/constants';

interface BadgeProps {
  children: React.ReactNode;
  className?: string;
}

export function Badge({ children, className = '' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${className}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600 border-gray-200';
  return <Badge className={cls}>{formatStatus(status)}</Badge>;
}

export function SeverityBadge({ severity }: { severity: string | null }) {
  if (!severity) return <span className="text-xs text-gray-400">—</span>;
  const cls = SEVERITY_COLORS[severity] ?? 'bg-gray-100 text-gray-600 border-gray-200';
  return <Badge className={cls}>{severity.charAt(0).toUpperCase() + severity.slice(1)}</Badge>;
}
