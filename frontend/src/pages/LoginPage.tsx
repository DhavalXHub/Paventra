import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { MapPin } from 'lucide-react';
import { useAuth } from '../features/auth/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/FormElements';
import { Alert } from '../components/Feedback';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('coordinator@paventra.local');
  const [password, setPassword] = useState('Paventra2024!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      const role = localStorage.getItem('user_role');
      if (role === 'citizen') {
        navigate('/my-reports');
      } else if (role === 'repair_team') {
        navigate('/team/jobs');
      } else {
        navigate('/coordinator');
      }
    } catch {
      setError('Invalid email or password.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="flex justify-center">
            <div className="w-10 h-10 bg-accent rounded-xl flex items-center justify-center">
              <MapPin className="w-6 h-6 text-white" />
            </div>
          </div>
          <h1 className="text-xl font-semibold text-gray-900">Paventra</h1>
          <p className="text-sm text-gray-500">Coordinator portal</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <Alert type="error" message={error} />}
            <Input
              label="Email address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            <Button type="submit" loading={loading} className="w-full">
              Sign in
            </Button>
          </form>
        </div>

        <div className="text-center text-xs text-gray-500 space-y-1">
          <p>
            Citizens:{' '}
            <Link to="/register" className="text-accent font-medium hover:underline">
              Create an account
            </Link>{' '}
            or{' '}
            <Link to="/report" className="text-accent hover:underline">
              Submit without an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
