import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { MapPin, ArrowLeft, ShieldAlert, FileText, Search, ChevronDown, ChevronUp, Lock, X } from 'lucide-react';
import { useAuth } from '../features/auth/AuthContext';
import { Button } from '../components/Button';
import { Input } from '../components/FormElements';
import { Alert } from '../components/Feedback';
import api from '../lib/api';

declare global {
  interface Window {
    google?: {
      accounts?: {
        id?: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string; select_by?: string }) => void;
            error_callback?: (error: any) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              type?: 'standard' | 'icon';
              shape?: 'rectangular' | 'pill' | 'circle' | 'square';
              theme?: 'outline' | 'filled_blue' | 'filled_black';
              text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
              size?: 'large' | 'medium' | 'small';
              logo_alignment?: 'left' | 'center';
              width?: number | string;
            }
          ) => void;
          prompt: () => void;
        };
      };
    };
  }
}

interface AuthConfig {
  google_enabled: boolean;
  google_client_id: string | null;
  environment: string;
}

export default function LoginPage() {
  const { login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(() => {
    const envClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
    return envClientId
      ? {
          google_enabled: true,
          google_client_id: envClientId,
          environment: 'development',
        }
      : null;
  });
  const [googleNotice, setGoogleNotice] = useState<string | null>(null);
  const [showDemoAccounts, setShowDemoAccounts] = useState(false);

  // Account Linking Modal state
  const [showLinkingModal, setShowLinkingModal] = useState(false);
  const [linkingPassword, setLinkingPassword] = useState('');
  const [pendingCredential, setPendingCredential] = useState<string | null>(null);
  const [linkingError, setLinkingError] = useState<string | null>(null);

  const googleBtnRef = useRef<HTMLDivElement>(null);
  const [gisRendered, setGisRendered] = useState(false);
  const [gisFailed, setGisFailed] = useState(false);

  const redirectUser = useCallback((role: string) => {
    if (fromPath && fromPath !== '/login' && fromPath !== '/register') {
      navigate(fromPath);
      return;
    }
    if (role === 'citizen') {
      navigate('/my-reports');
    } else if (role === 'repair_team') {
      navigate('/team/jobs');
    } else {
      navigate('/coordinator');
    }
  }, [fromPath, navigate]);

  // Fetch backend auth config on mount
  useEffect(() => {
    api.get<AuthConfig>('/auth/config')
      .then((res) => {
        setAuthConfig(res.data);
      })
      .catch(() => {
        setAuthConfig({
          google_enabled: !!import.meta.env.VITE_GOOGLE_CLIENT_ID,
          google_client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || null,
          environment: 'development',
        });
      });
  }, []);

  // Google credential callback
  const handleGoogleCredentialResponse = useCallback(async (response: { credential: string }) => {
    setError(null);
    setGoogleNotice(null);
    setGoogleLoading(true);
    try {
      const user = await loginWithGoogle(response.credential);
      redirectUser(user.role);
    } catch (err: any) {
      if (err?.response?.status === 409) {
        // Account exists with this email — require password linking verification
        setPendingCredential(response.credential);
        setShowLinkingModal(true);
        setLinkingError(err?.response?.data?.detail ?? 'An account with this email already exists. Enter your password to link Google.');
      } else {
        const detail = err?.response?.data?.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (Array.isArray(detail)) {
          setError(detail.map((d: any) => d.msg || JSON.stringify(d)).join(', '));
        } else {
          setError('Google authentication failed. Please check your credentials or try email login.');
        }
      }
    } finally {
      setGoogleLoading(false);
    }
  }, [loginWithGoogle, redirectUser]);

  const effectiveClientId = authConfig?.google_client_id || import.meta.env.VITE_GOOGLE_CLIENT_ID || null;
  const isClientIdValid = !!(
    effectiveClientId &&
    effectiveClientId.includes('.apps.googleusercontent.com') &&
    effectiveClientId.length > 25
  );
  const isGoogleAvailable = !!(authConfig?.google_enabled && isClientIdValid);

  // Detect non-standard development origin (e.g. port 5174 instead of 5173)
  const isNonStandardOrigin =
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') &&
    window.location.port !== '5173' &&
    window.location.port !== '';

  // Initialize GIS and render official button reliably
  useEffect(() => {
    if (!isGoogleAvailable || !effectiveClientId) return;

    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 40; // 40 * 100ms = 4 seconds

    const renderGis = () => {
      if (cancelled) return false;
      if (window.google?.accounts?.id && googleBtnRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: effectiveClientId,
            callback: handleGoogleCredentialResponse,
            error_callback: (err) => {
              console.warn('Google Sign-In notice:', err);
              if (err?.type === 'origin_mismatch') {
                setError(
                  `Google Sign-In origin mismatch (Error 400): Origin "${window.location.origin}" is not authorized in Google Cloud Console. Please open http://localhost:5173/login or add "${window.location.origin}" under Authorized JavaScript Origins in Google Cloud Console.`
                );
              }
            },
            auto_select: false,
            cancel_on_tap_outside: true,
          });

          googleBtnRef.current.innerHTML = '';
          window.google.accounts.id.renderButton(googleBtnRef.current, {
            type: 'standard',
            shape: 'rectangular',
            theme: 'outline',
            text: 'continue_with',
            size: 'large',
            logo_alignment: 'left',
            width: 384,
          });
          setGisRendered(true);
          setGisFailed(false);
          return true;
        } catch (e) {
          console.error('Error during GIS renderButton:', e);
        }
      }
      return false;
    };

    // Attempt immediate render if Google client library is ready
    if (renderGis()) return;

    // Retry periodically until Google client library is loaded
    const interval = setInterval(() => {
      attempts++;
      if (renderGis() || attempts >= maxAttempts) {
        clearInterval(interval);
        if (!window.google?.accounts?.id && !cancelled) {
          setGisFailed(true);
        }
      }
    }, 100);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [isGoogleAvailable, effectiveClientId, handleGoogleCredentialResponse]);

  async function handleEmailLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setGoogleNotice(null);
    try {
      await login(email, password);
      const role = localStorage.getItem('user_role') || 'citizen';
      redirectUser(role);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleFallbackClick() {
    setError(null);
    setGoogleNotice(null);
    if (!effectiveClientId || (authConfig && !authConfig.google_enabled)) {
      setGoogleNotice(
        'Google OAuth is not configured on this deployment. Please sign in with email credentials or continue as guest.'
      );
      return;
    }
    // If GIS script hasn't rendered yet, attempt prompt
    if (window.google?.accounts?.id) {
      window.google.accounts.id.prompt();
    } else {
      setGoogleNotice(
        'Google Identity Services client library could not be loaded. Please ensure you are not blocking scripts with an ad-blocker or check network connection.'
      );
    }
  }

  async function handleLinkAccountSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!pendingCredential || !linkingPassword) return;
    setGoogleLoading(true);
    setLinkingError(null);
    try {
      const user = await loginWithGoogle({
        credential: pendingCredential,
        link_existing: true,
        password_for_linking: linkingPassword,
      });
      setShowLinkingModal(false);
      redirectUser(user.role);
    } catch (err: any) {
      setLinkingError(err?.response?.data?.detail ?? 'Incorrect password. Could not link account.');
    } finally {
      setGoogleLoading(false);
    }
  }

  function prefillDemo(demoEmail: string, demoPass: string) {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
    setGoogleNotice(null);
  }

  return (
    <div className="min-h-screen bg-[#faf9f6] flex flex-col justify-between py-8 px-4 sm:px-6">
      {/* Top Header / Home navigation */}
      <div className="max-w-md w-full mx-auto flex items-center justify-between pb-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-stone-600 hover:text-stone-900 bg-white border border-stone-200 px-3 py-1.5 rounded-lg shadow-xs transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>
        <div className="text-right">
          <span className="text-[11px] font-semibold tracking-wider uppercase text-stone-600">
            Civic Access
          </span>
        </div>
      </div>

      {/* Main Container */}
      <div className="max-w-md w-full mx-auto space-y-6">
        {/* Brand Banner */}
        <div className="text-center space-y-2">
          <Link to="/" className="inline-flex items-center gap-2 group">
            <div className="w-10 h-10 bg-[#14462a] rounded-xl flex items-center justify-center shadow-xs group-hover:bg-[#0f3620] transition-colors">
              <MapPin className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-stone-900 tracking-tight">Paventra</span>
          </Link>
          <h1 className="text-xl font-semibold text-stone-900">Sign in to your account</h1>
          <p className="text-xs text-stone-600">
            Access your damage reports, coordinate inspections or manage repair work orders.
          </p>
        </div>

        {fromPath && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-700 flex-shrink-0" />
            <span>Please sign in to access <strong>{fromPath}</strong>.</span>
          </div>
        )}

        {/* Card */}
        <div className="bg-white border border-stone-200 rounded-2xl shadow-xs p-6 sm:p-7 space-y-5">
          {error && <Alert type="error" message={error} />}
          {googleNotice && <Alert type="info" message={googleNotice} />}

          {/* Warning banner if loaded on non-5173 port (e.g. 5174) */}
          {isNonStandardOrigin && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-800 space-y-1.5">
              <div className="flex items-center gap-1.5 font-semibold text-amber-900">
                <ShieldAlert className="w-4 h-4 text-amber-700 flex-shrink-0" />
                <span>Port Mismatch Notice ({window.location.origin})</span>
              </div>
              <p className="leading-relaxed">
                Google OAuth origins in Google Cloud Console are authorized for port <strong>5173</strong>.
              </p>
              <p className="pt-0.5">
                Switch to{' '}
                <a
                  href={`http://localhost:5173${location.pathname}`}
                  className="underline font-bold text-amber-950 hover:text-black"
                >
                  http://localhost:5173{location.pathname}
                </a>{' '}
                to prevent Google <code>Error 400: origin_mismatch</code>, or register{' '}
                <code>{window.location.origin}</code> in Google Cloud Console.
              </p>
            </div>
          )}

          {/* MODE 1: Google OAuth Section */}
          <div className="space-y-2">
            {isGoogleAvailable ? (
              <div className="w-full flex flex-col items-center justify-center">
                {!gisFailed ? (
                  <div
                    ref={googleBtnRef}
                    className="w-full flex justify-center min-h-[44px]"
                  />
                ) : (
                  <button
                    type="button"
                    onClick={handleGoogleFallbackClick}
                    className="w-full max-w-[384px] flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl border border-stone-300 bg-white text-stone-800 text-sm font-medium hover:bg-stone-50 active:bg-stone-100 transition-colors shadow-xs"
                  >
                    <svg className="w-4 h-4" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                    </svg>
                    <span>Continue with Google</span>
                    <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">Click to Retry</span>
                  </button>
                )}
                {googleLoading && (
                  <p className="text-xs text-stone-500 pt-1.5 animate-pulse">
                    Verifying Google identity with Paventra...
                  </p>
                )}
              </div>
            ) : (
              <button
                type="button"
                onClick={handleGoogleFallbackClick}
                className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-xl border border-stone-300 bg-white text-stone-800 text-sm font-medium hover:bg-stone-50 active:bg-stone-100 transition-colors shadow-xs"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Continue with Google</span>
                <span className="text-[10px] font-normal text-stone-600 bg-stone-100 px-1.5 py-0.5 rounded">
                  Unconfigured
                </span>
              </button>
            )}
          </div>

          {/* Divider */}
          <div className="relative flex items-center justify-center">
            <div className="border-t border-stone-200 w-full" />
            <span className="bg-white px-3 text-[11px] font-semibold text-stone-600 uppercase tracking-wider">
              Or continue with email
            </span>
          </div>

          {/* MODE 2: Email Form */}
          <form onSubmit={handleEmailLogin} className="space-y-4">
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
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
            <Button
              type="submit"
              loading={loading}
              className="w-full bg-[#14462a] hover:bg-[#0f3620] text-white py-2.5 rounded-xl text-sm font-semibold shadow-xs"
            >
              Sign in with Email
            </Button>
          </form>

          {/* Quick Demo Accounts Drawer */}
          <div className="pt-2 border-t border-stone-100">
            <button
              type="button"
              onClick={() => setShowDemoAccounts(!showDemoAccounts)}
              className="w-full flex items-center justify-between text-xs text-stone-600 hover:text-stone-900 py-1"
            >
              <span className="font-medium">Prefill testing accounts</span>
              {showDemoAccounts ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showDemoAccounts && (
              <div className="mt-2 space-y-1.5 bg-stone-50 p-2.5 rounded-lg border border-stone-200 text-xs">
                <button
                  type="button"
                  onClick={() => prefillDemo('coordinator@paventra.local', 'Paventra2024!')}
                  className="w-full text-left p-1.5 rounded hover:bg-stone-200/70 flex items-center justify-between transition-colors"
                >
                  <div>
                    <span className="font-semibold text-stone-800">Coordinator</span>
                    <span className="text-[11px] text-stone-600 block">coordinator@paventra.local</span>
                  </div>
                  <span className="text-[10px] text-stone-600 bg-white px-1.5 py-0.5 rounded border border-stone-200">Select</span>
                </button>
                <button
                  type="button"
                  onClick={() => prefillDemo('team.alpha@paventra.local', 'TeamAlpha2024!')}
                  className="w-full text-left p-1.5 rounded hover:bg-stone-200/70 flex items-center justify-between transition-colors"
                >
                  <div>
                    <span className="font-semibold text-stone-800">Repair Team</span>
                    <span className="text-[11px] text-stone-600 block">team.alpha@paventra.local</span>
                  </div>
                  <span className="text-[10px] text-stone-600 bg-white px-1.5 py-0.5 rounded border border-stone-200">Select</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* MODE 3: Continue as Guest (First-class choice) */}
        <div className="bg-stone-100/70 border border-stone-200 rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-stone-700">
              Continue as Guest
            </h2>
          </div>
          <p className="text-xs text-stone-600">
            Account registration is completely optional. You can report potholes or track repair status anonymously.
          </p>
          <div className="grid grid-cols-2 gap-2 pt-1">
            <Link
              to="/report"
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-stone-300 text-xs font-semibold text-stone-800 hover:bg-stone-50 hover:border-stone-400 transition-colors shadow-xs"
            >
              <FileText className="w-3.5 h-3.5 text-stone-600" />
              <span>Report damage</span>
            </Link>
            <Link
              to="/track"
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-white border border-stone-300 text-xs font-semibold text-stone-800 hover:bg-stone-50 hover:border-stone-400 transition-colors shadow-xs"
            >
              <Search className="w-3.5 h-3.5 text-stone-600" />
              <span>Track a report</span>
            </Link>
          </div>
        </div>

        {/* Citizen Registration Link */}
        <div className="text-center text-xs text-stone-600">
          <span>Don't have an account yet? </span>
          <Link to="/register" className="text-[#14462a] font-semibold hover:underline">
            Create citizen account
          </Link>
        </div>
      </div>

      {/* Account Linking Modal */}
      {showLinkingModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-stone-200 shadow-xl max-w-sm w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-stone-100">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-[#14462a]" />
                <h3 className="text-sm font-bold text-stone-900">Link Google Account</h3>
              </div>
              <button
                onClick={() => {
                  setShowLinkingModal(false);
                  setPendingCredential(null);
                  setLinkingPassword('');
                }}
                className="text-stone-400 hover:text-stone-600 p-1 rounded-md"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-stone-600 leading-relaxed">
              An account with your Google email address already exists. To verify ownership and link your Google sign-in, enter your password below:
            </p>

            {linkingError && <Alert type="error" message={linkingError} />}

            <form onSubmit={handleLinkAccountSubmit} className="space-y-3">
              <Input
                label="Account Password"
                type="password"
                value={linkingPassword}
                onChange={(e) => setLinkingPassword(e.target.value)}
                placeholder="••••••••"
                required
              />

              <div className="flex gap-2 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setShowLinkingModal(false);
                    setPendingCredential(null);
                    setLinkingPassword('');
                  }}
                  className="flex-1 text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={googleLoading}
                  className="flex-1 bg-[#14462a] hover:bg-[#0f3620] text-white text-xs font-semibold"
                >
                  Verify & Link
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="max-w-md w-full mx-auto text-center pt-6 text-[11px] text-stone-600">
        Paventra Civic Road Intelligence Platform
      </div>
    </div>
  );
}
