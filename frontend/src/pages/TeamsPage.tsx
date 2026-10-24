import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Users } from 'lucide-react';
import api from '../lib/api';
import type { Team } from '../types';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Input, Textarea } from '../components/FormElements';
import { Alert, EmptyState } from '../components/Feedback';
import { formatDate } from '../lib/constants';

export default function TeamsPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const { data: teams, isLoading } = useQuery<Team[]>({
    queryKey: ['teams'],
    queryFn: () => api.get('/teams').then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (body: object) => api.post('/teams', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teams'] });
      setShowForm(false);
      setName('');
      setDescription('');
      setContactEmail('');
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      setFormError(err?.response?.data?.detail ?? 'Failed to create team');
    },
  });

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-gray-900">Repair teams</h1>
          <p className="text-xs text-gray-500">{teams?.length ?? 0} active teams</p>
        </div>
        <Button icon={<Plus className="w-4 h-4" />} onClick={() => setShowForm(!showForm)}>
          Add team
        </Button>
      </div>

      {showForm && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-4">New repair team</h3>
          {formError && <Alert type="error" message={formError} className="mb-3" />}
          <div className="space-y-3">
            <Input
              label="Team name *"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Team Delta"
            />
            <Textarea
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Describe the team's area or specialty"
            />
            <Input
              label="Contact email"
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="team@example.com"
            />
            <div className="flex gap-2">
              <Button
                variant="secondary"
                onClick={() => { setShowForm(false); setFormError(null); }}
              >
                Cancel
              </Button>
              <Button
                disabled={!name.trim()}
                loading={createMutation.isPending}
                onClick={() => createMutation.mutate({ name: name.trim(), description, contact_email: contactEmail })}
              >
                Create team
              </Button>
            </div>
          </div>
        </Card>
      )}

      {isLoading ? (
        <div className="text-sm text-gray-500">Loading teams…</div>
      ) : !teams?.length ? (
        <EmptyState
          icon={<Users className="w-10 h-10" />}
          title="No repair teams yet"
          description="Create your first team to start assigning reports"
        />
      ) : (
        <div className="space-y-3">
          {teams.map((t) => (
            <Card key={t.id}>
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-gray-900">{t.name}</p>
                  {t.description && <p className="text-xs text-gray-600">{t.description}</p>}
                  <div className="flex flex-wrap gap-3 mt-2">
                    {t.contact_email && (
                      <span className="text-xs text-gray-500">{t.contact_email}</span>
                    )}
                    <span className="text-xs text-gray-400">Created {formatDate(t.created_at)}</span>
                  </div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                  t.is_active
                    ? 'bg-green-50 text-green-700 border-green-200'
                    : 'bg-gray-100 text-gray-500 border-gray-200'
                }`}>
                  {t.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
