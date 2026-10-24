import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from 'lucide-react';

type AlertType = 'error' | 'success' | 'info' | 'warning';

interface AlertProps {
  type: AlertType;
  title?: string;
  message: string;
  className?: string;
}

const CONFIG = {
  error: {
    cls: 'bg-red-50 border-red-200 text-red-800',
    icon: <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />,
  },
  success: {
    cls: 'bg-green-50 border-green-200 text-green-800',
    icon: <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />,
  },
  info: {
    cls: 'bg-blue-50 border-blue-200 text-blue-800',
    icon: <Info className="w-4 h-4 text-blue-500 flex-shrink-0" />,
  },
  warning: {
    cls: 'bg-amber-50 border-amber-200 text-amber-800',
    icon: <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />,
  },
};

export function Alert({ type, title, message, className = '' }: AlertProps) {
  const { cls, icon } = CONFIG[type];
  return (
    <div className={`flex gap-3 p-3 rounded-md border text-sm ${cls} ${className}`}>
      {icon}
      <div>
        {title && <p className="font-medium mb-0.5">{title}</p>}
        <p>{message}</p>
      </div>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="text-gray-300 mb-4">{icon}</div>}
      <p className="text-sm font-medium text-gray-700">{title}</p>
      {description && <p className="text-xs text-gray-500 mt-1 max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className}`} />;
}

export function PageSkeleton() {
  return (
    <div className="space-y-4 p-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
