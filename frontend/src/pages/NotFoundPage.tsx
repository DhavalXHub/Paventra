import React from 'react';
import { Link } from 'react-router-dom';
import { MapPin, ArrowLeft, Home, Search } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-[#fafaf8] flex flex-col items-center justify-center px-4">
      {/* Brand */}
      <Link to="/" className="flex items-center gap-2 mb-12 group">
        <div className="w-9 h-9 rounded-lg bg-[#14462a] flex items-center justify-center shadow-sm group-hover:bg-[#0f3620] transition-colors">
          <MapPin className="w-5 h-5 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="font-bold text-stone-900 text-lg tracking-tight leading-none">Paventra</span>
          <span className="text-[10px] font-medium text-stone-500 tracking-wider uppercase mt-0.5">Road Intelligence</span>
        </div>
      </Link>

      {/* 404 */}
      <div className="text-center max-w-md">
        <div className="text-8xl font-black text-[#14462a]/10 mb-2 select-none">404</div>
        <h1 className="text-2xl font-bold text-stone-900 mb-3">Page not found</h1>
        <p className="text-stone-500 mb-8">
          The page you're looking for doesn't exist or has moved. Use the links below to
          get back on track.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[#14462a] text-white font-semibold text-sm hover:bg-[#0f3620] transition-colors"
          >
            <Home className="w-4 h-4" /> Go home
          </Link>
          <Link
            to="/track"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg border border-stone-300 text-stone-700 font-semibold text-sm hover:border-stone-400 transition-colors"
          >
            <Search className="w-4 h-4" /> Track a report
          </Link>
          <Link
            to="/report"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg border border-stone-300 text-stone-700 font-semibold text-sm hover:border-stone-400 transition-colors"
          >
            Report damage
          </Link>
        </div>
      </div>
    </div>
  );
}
