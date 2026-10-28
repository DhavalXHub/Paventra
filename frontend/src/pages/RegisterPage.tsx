import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { MapPin, ArrowLeft, ShieldCheck, FileText, Search } from 'lucide-react';
import api from '../lib/api';
import { useAuth } from '../features/auth/AuthContext';
import { getAuthorizedRedirect } from '../features/auth/routing';
import { Button } from '../components/Button';
import { Input } from '../components/FormElements';
import { Alert } from '../components/Feedback';

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname;

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
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
        role: 'citizen',
      });
      // Automatically log them in after registration
      const user = await login(email, password);
      const destination = getAuthorizedRedirect(user.role, fromPath);
      navigate(destination, { replace: true });
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to register. Please check your details.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#faf9f6] flex flex-col justify-between py-8 px-4 sm:px-6">
      {/* Top Header / Home navigation */}
      <div className="max-w-md w-full mx-auto flex items-center justify-between pb-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-stone-600 hover:text-stone-900 bg-white border border-stone-200 px-3 py-1.5 rounded-lg shadow-sm transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>
        <div className="text-right">
          <span className="text-[11px] font-semibold tracking-wider uppercase text-stone-600">
            Citizen Registration
          </span>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-md w-full mx-auto space-y-6">
        {/* Brand Banner */}
        <div className="text-center space-y-2">
          <Link to="/" className="inline-flex items-center gap-2 group">
            <div className="w-10 h-10 bg-[#14462a] rounded-xl flex items-center justify-center shadow-sm group-hover:bg-[#0f3620] transition-colors">
              <MapPin className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-stone-900 tracking-tight">Paventra</span>
          </Link>
          <h1 className="text-xl font-semibold text-stone-900">Create Citizen Account</h1>
          <p className="text-xs text-stone-600">
            Track status updates, view verified repair photos, and organize all your community road reports.
          </p>
        </div>

        {/* Card */}
        <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-6 sm:p-7 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <Alert type="error" message={error} />}
            <Input
              label="Full name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Rahul Sharma"
              autoComplete="name"
              required
            />
            <Input
              label="Email address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. rahul@example.com"
              autoComplete="email"
              required
            />
            <Input
              label="Password (min. 8 characters)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
              required
              minLength={8}
            />
            <Button
              type="submit"
              loading={loading}
              className="w-full bg-[#14462a] hover:bg-[#0f3620] text-white py-2.5 rounded-xl text-sm font-semibold shadow-xs"
            >
              Create Account
            </Button>
          </form>

          <div className="pt-3 border-t border-stone-100 text-center text-xs text-stone-600">
            Already have an account?{' '}
            <Link to="/login" className="text-[#14462a] font-semibold hover:underline">
              Sign in
            </Link>
          </div>
        </div>

        {/* Continue as Guest option */}
        <div className="bg-stone-100/70 border border-stone-200 rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-stone-700">
              Prefer Not to Register?
            </h2>
          </div>
          <p className="text-xs text-stone-600">
            Guest reporting is always available without an account. You will receive a unique tracking reference upon submission.
          </p>
          <div className="pt-1">
            <Link
              to="/report"
              className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-stone-300 text-xs font-semibold text-stone-800 hover:bg-stone-50 hover:border-stone-400 transition-colors shadow-xs"
            >
              <FileText className="w-3.5 h-3.5 text-stone-600" />
              <span>Report road damage as guest</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="max-w-md w-full mx-auto text-center pt-6 text-[11px] text-stone-600">
        Paventra Civic Road Intelligence Platform
      </div>
    </div>
  );
}
