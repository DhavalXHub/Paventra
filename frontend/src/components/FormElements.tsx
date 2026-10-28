import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Input({ label, error, hint, className = '', id, type, ...props }: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');
  const isPassword = type === 'password';
  const [showPassword, setShowPassword] = useState(false);

  const resolvedType = isPassword ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-gray-700">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={inputId}
          type={resolvedType}
          className={`w-full px-3 py-2 text-sm border rounded-md bg-white text-gray-900
            placeholder-gray-400 transition-colors
            focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
            disabled:bg-gray-50 disabled:text-gray-500
            ${isPassword ? 'pr-10' : ''}
            ${error ? 'border-red-400' : 'border-gray-200'}
            ${className}`}
          {...props}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            title={showPassword ? 'Hide password' : 'Show password'}
            className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 transition-colors focus:outline-none"
            tabIndex={-1}
          >
            {showPassword ? (
              <EyeOff className="w-4 h-4" aria-hidden="true" />
            ) : (
              <Eye className="w-4 h-4" aria-hidden="true" />
            )}
          </button>
        )}
      </div>
      {hint && !error && <p className="text-xs text-gray-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export function Textarea({ label, error, hint, className = '', id, ...props }: TextareaProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-gray-700">
          {label}
        </label>
      )}
      <textarea
        id={inputId}
        className={`w-full px-3 py-2 text-sm border rounded-md bg-white text-gray-900
          placeholder-gray-400 transition-colors resize-none
          focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
          ${error ? 'border-red-400' : 'border-gray-200'}
          ${className}`}
        {...props}
      />
      {hint && !error && <p className="text-xs text-gray-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

export function Select({ label, error, options, className = '', id, ...props }: SelectProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-');
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-gray-700">
          {label}
        </label>
      )}
      <select
        id={inputId}
        className={`w-full px-3 py-2 text-sm border rounded-md bg-white text-gray-900
          focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent
          ${error ? 'border-red-400' : 'border-gray-200'}
          ${className}`}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
