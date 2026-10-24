import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import api from '../lib/api';
import { Card, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import { EmptyState, Skeleton } from '../components/Feedback';
import { formatRelative } from '../lib/constants';

interface Notification {
  id: string;
  title: string;
  body: string;
  notification_type: string;
  is_read: boolean;
  created_at: string;
  report_id: string | null;
}

const TYPE_ICON: Record<string, React.ReactNode> = {
  report_submitted: <CheckCircle2 className="w-4 h-4 text-accent" />,
  status_change: <Info className="w-4 h-4 text-blue-500" />,
  assignment: <AlertCircle className="w-4 h-4 text-amber-500" />,
  default: <Bell className="w-4 h-4 text-gray-400" />,
};

export default function NotificationsPage() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<Notification[]>({
    queryKey: ['notifications'],
    queryFn: () => api.get('/notifications').then((r) => r.data),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => api.patch(`/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAllMutation = useMutation({
    mutationFn: () => api.patch('/notifications/read-all'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const unread = data?.filter((n) => !n.is_read).length ?? 0;

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Notifications</h1>
          {unread > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">{unread} unread</p>
          )}
        </div>
        {unread > 0 && (
          <Button
            variant="ghost"
            size="sm"
            loading={markAllMutation.isPending}
            onClick={() => markAllMutation.mutate()}
          >
            <CheckCheck className="w-4 h-4 mr-1.5" />
            Mark all read
          </Button>
        )}
      </div>

      <Card padding={false}>
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-14 rounded-md" />
            ))}
          </div>
        ) : !data?.length ? (
          <EmptyState
            icon={<Bell className="w-8 h-8" />}
            title="No notifications"
            description="You're all caught up."
          />
        ) : (
          <ul className="divide-y divide-gray-100">
            {data.map((n) => (
              <li
                key={n.id}
                className={`flex items-start gap-3 px-4 py-3 hover:bg-gray-50 transition-colors ${
                  !n.is_read ? 'bg-accent-light/30' : ''
                }`}
              >
                <div className="mt-0.5 flex-shrink-0">
                  {TYPE_ICON[n.notification_type] ?? TYPE_ICON.default}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${!n.is_read ? 'font-medium text-gray-900' : 'text-gray-700'}`}>
                    {n.title}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                  <p className="text-xs text-gray-400 mt-1">{formatRelative(n.created_at)}</p>
                </div>
                {!n.is_read && (
                  <button
                    onClick={() => markReadMutation.mutate(n.id)}
                    className="flex-shrink-0 text-xs text-accent hover:underline mt-0.5"
                  >
                    Mark read
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
