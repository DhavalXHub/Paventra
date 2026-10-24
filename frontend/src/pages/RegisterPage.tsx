import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { MapPin } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../features/auth/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/FormElements';
import { Alert } from '../components/Feedback';

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await api.post('/auth/register', {
        full_name: fullName,
        email: email.trim().toLowerCase(),
        password,
        role: 'citizen',
      });
      // Automatically log them in after registration
      await login(email, password);
      navigate('/my-reports');
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to register. Please check your details.');
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
          <h1 className="text-xl font-semibold text-gray-900">Create Citizen Account</h1>
          <p className="text-xs text-gray-500">Track and manage all your road damage reports</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <Alert type="error" message={error} />}
            <Input
              label="Full name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Rahul Sharma"
              required
            />
            <Input
              label="Email address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. rahul@example.com"
              required
            />
            <Input
              label="Password (min. 8 characters)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
            <Button type="submit" loading={loading} className="w-full">
              Create Account
            </Button>
          </form>

          <div className="mt-4 text-center text-xs text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="text-accent font-medium hover:underline">
              Sign in
            </Link>
          </div>
        </div>

        <p className="text-center text-xs text-gray-400">
          <Link to="/report" className="hover:underline">Submit report without an account</Link>
        </p>
      </div>
    </div>
  );
}
