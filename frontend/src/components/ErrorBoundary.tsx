import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-[#faf9f6] flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white rounded-2xl border border-stone-200 shadow-sm p-6 sm:p-8 space-y-5 text-center">
            <div className="w-12 h-12 bg-red-50 text-red-600 rounded-xl mx-auto flex items-center justify-center">
              <AlertCircle className="w-6 h-6" />
            </div>

            <div className="space-y-1.5">
              <h2 className="text-lg font-semibold text-stone-900">Something went wrong</h2>
              <p className="text-xs text-stone-600">
                An unexpected interface error occurred. You can reload this page or return to the Paventra homepage.
              </p>
            </div>

            {import.meta.env.DEV && this.state.error && (
              <div className="bg-red-50/70 border border-red-200 rounded-lg p-3 text-left">
                <p className="text-xs font-mono font-medium text-red-800 break-all">
                  {this.state.error.message}
                </p>
              </div>
            )}

            <div className="flex gap-2.5 pt-2">
              <a
                href="/"
                className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl border border-stone-200 bg-white text-stone-700 text-xs font-semibold hover:bg-stone-50 transition-colors shadow-xs"
              >
                <Home className="w-3.5 h-3.5" />
                <span>Go to Home</span>
              </a>
              <button
                type="button"
                onClick={this.handleReset}
                className="flex-1 inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-[#14462a] text-white text-xs font-semibold hover:bg-[#0f3620] transition-colors shadow-xs"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Reload Page</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
