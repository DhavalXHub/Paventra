import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Camera, Upload, MapPin, CheckCircle2, ArrowLeft, AlertTriangle, Loader2, RefreshCw, User } from 'lucide-react';
import { LocationPickerMap } from '../components/Map';
import { Button } from '../components/Button';
import { Input, Textarea, Select } from '../components/FormElements';
import { Alert, Skeleton } from '../components/Feedback';
import { DAMAGE_TYPE_OPTIONS } from '../lib/constants';
import { useAuth } from '../features/auth/AuthContext';
import api from '../lib/api';
import type { SubmitConfirmation } from '../types';

type Step = 'photo' | 'location' | 'review' | 'done';

interface FormState {
  image: File | null;
  imagePreview: string | null;
  description: string;
  damage_type: string;
  lat: number | null;
  lng: number | null;
  location_source: string;
  location_accuracy: number | null;
  address_hint: string;
  submitter_email: string;
}

export default function ReportPage() {
  const { user, isAuthenticated } = useAuth();
  const [step, setStep] = useState<Step>('photo');
  const [form, setForm] = useState<FormState>({
    image: null,
    imagePreview: null,
    description: '',
    damage_type: 'unknown',
    lat: null,
    lng: null,
    location_source: 'unknown',
    location_accuracy: null,
    address_hint: '',
    submitter_email: user?.email ?? '',
  });
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubmitConfirmation | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  function handleFileSelect(file: File) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setError('Please select a JPEG, PNG or WebP image.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Image must be smaller than 10 MB.');
      return;
    }
    setError(null);
    const url = URL.createObjectURL(file);
    setForm((f) => ({ ...f, image: file, imagePreview: url }));
  }

  function requestGps() {
    if (!navigator.geolocation) {
      setGpsError('Location is not supported by your browser.');
      return;
    }
    setGpsLoading(true);
    setGpsError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((f) => ({
          ...f,
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          location_source: 'gps',
          location_accuracy: pos.coords.accuracy,
        }));
        setGpsLoading(false);
      },
      (err) => {
        setGpsError('Could not get your location. You can pin it on the map below.');
        setGpsLoading(false);
      },
      { timeout: 10000 }
    );
  }

  useEffect(() => { requestGps(); }, []);

  async function handleSubmit() {
    if (!form.image) return;
    setSubmitting(true);
    setError(null);
    try {
      const data = new FormData();
      data.append('image', form.image);
      if (form.description) data.append('description', form.description);
      data.append('damage_type', form.damage_type);
      if (form.lat !== null) data.append('latitude', String(form.lat));
      if (form.lng !== null) data.append('longitude', String(form.lng));
      data.append('location_source', form.location_source);
      if (form.location_accuracy !== null) data.append('location_accuracy_meters', String(form.location_accuracy));
      if (form.address_hint) data.append('address_hint', form.address_hint);
      if (form.submitter_email) data.append('submitter_email', form.submitter_email);

      const res = await api.post<SubmitConfirmation>('/reports', data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
      setStep('done');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? 'Submission failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  // ─── DONE ───────────────────────────────────────────────────────────────────
  if (step === 'done' && result) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-start justify-center px-4 py-12">
        <div className="w-full max-w-md bg-white rounded-xl border border-gray-200 shadow-sm p-8 text-center space-y-4">
          <div className="flex justify-center">
            <div className="w-14 h-14 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Report submitted</h2>
          <p className="text-sm text-gray-600">{result.message}</p>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-left space-y-1">
            <p className="text-xs text-gray-500">Your reference number</p>
            <p className="text-xl font-mono font-bold text-gray-900 tracking-wider">{result.public_ref}</p>
          </div>
          {result.ai_assessment && result.ai_assessment['model_available'] && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left space-y-1">
              <p className="text-xs font-medium text-blue-800">AI preliminary assessment</p>
              <p className="text-xs text-blue-700">
                Detected: {String(result.ai_assessment['damage_type'] ?? 'unknown')}
                {result.ai_assessment['confidence'] && (
                  <> · Confidence: {(Number(result.ai_assessment['confidence']) * 100).toFixed(0)}%</>
                )}
              </p>
              <p className="text-xs text-blue-600 italic">{String(result.ai_assessment['disclaimer'] ?? '')}</p>
            </div>
          )}
          {result.ai_assessment && !result.ai_assessment['model_available'] && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-left space-y-0.5">
              <p className="text-xs font-semibold text-gray-700">Manual Field Review Path</p>
              <p className="text-xs text-gray-500">
                {String(result.ai_assessment['message'] ?? 'Automated inference offline. A coordinator will manually review the photograph and coordinates.')}
              </p>
            </div>
          )}
          <div className="flex gap-3 pt-2">
            <a
              href={`/track/${result.public_ref}`}
              className="flex-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium
                border border-gray-200 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Track status
            </a>
            <button
              onClick={() => { setStep('photo'); setResult(null); setForm({ image: null, imagePreview: null, description: '', damage_type: 'unknown', lat: null, lng: null, location_source: 'unknown', location_accuracy: null, address_hint: '', submitter_email: '' }); }}
              className="flex-1 inline-flex items-center justify-center px-4 py-2 text-sm font-medium
                bg-accent text-white rounded-md hover:bg-accent-dark transition-colors"
            >
              Report another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 bg-accent rounded-md flex items-center justify-center">
            <MapPin className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold text-gray-900 text-sm">Paventra</span>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-3 text-xs">
          <Link to="/track" className="text-gray-600 hover:text-gray-900">
            Track report
          </Link>
          {isAuthenticated ? (
            <Link to="/my-reports" className="text-accent font-medium hover:underline flex items-center gap-1">
              <User className="w-3 h-3" />
              My reports
            </Link>
          ) : (
            <Link to="/login" className="text-accent font-medium hover:underline">
              Sign in
            </Link>
          )}
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-6 space-y-5">
        {/* Progress */}
        <div className="flex items-center gap-1">
          {(['photo', 'location', 'review'] as Step[]).map((s, i) => (
            <React.Fragment key={s}>
              <div className={`h-1 flex-1 rounded-full transition-colors ${
                step === 'done' || (step === 'review' && i < 3) || (step === 'location' && i < 2) || (step === 'photo' && i < 1)
                  ? 'bg-accent' : 'bg-gray-200'
              }`} />
            </React.Fragment>
          ))}
        </div>

        {error && <Alert type="error" message={error} />}

        {/* STEP 1: Photo */}
        {step === 'photo' && (
          <div className="space-y-4">
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Report road damage</h1>
              <p className="text-sm text-gray-500 mt-0.5">Take or upload a photo of the damage</p>
            </div>

            {form.imagePreview ? (
              <div className="relative">
                <img
                  src={form.imagePreview}
                  alt="Selected"
                  className="w-full rounded-lg border border-gray-200 object-cover max-h-64"
                />
                <button
                  onClick={() => setForm((f) => ({ ...f, image: null, imagePreview: null }))}
                  className="absolute top-2 right-2 bg-white border border-gray-200 rounded-full p-1.5
                    hover:bg-gray-50 transition-colors"
                >
                  <RefreshCw className="w-4 h-4 text-gray-600" />
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => cameraRef.current?.click()}
                  className="flex flex-col items-center gap-2 p-6 border-2 border-dashed border-gray-200
                    rounded-xl hover:border-accent hover:bg-accent-light/30 transition-colors group"
                >
                  <Camera className="w-8 h-8 text-gray-400 group-hover:text-accent" />
                  <span className="text-sm font-medium text-gray-600 group-hover:text-accent">Take photo</span>
                </button>
                <button
                  onClick={() => fileRef.current?.click()}
                  className="flex flex-col items-center gap-2 p-6 border-2 border-dashed border-gray-200
                    rounded-xl hover:border-accent hover:bg-accent-light/30 transition-colors group"
                >
                  <Upload className="w-8 h-8 text-gray-400 group-hover:text-accent" />
                  <span className="text-sm font-medium text-gray-600 group-hover:text-accent">Upload image</span>
                </button>
              </div>
            )}

            <input
              ref={cameraRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            />
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            />

            <Select
              label="Damage type (optional)"
              value={form.damage_type}
              options={DAMAGE_TYPE_OPTIONS}
              onChange={(e) => setForm((f) => ({ ...f, damage_type: e.target.value }))}
            />
            <Textarea
              label="Description (optional)"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              placeholder="Describe the damage, road name, etc."
              rows={3}
            />
            <Input
              label="Your email (optional — for status updates)"
              type="email"
              value={form.submitter_email}
              onChange={(e) => setForm((f) => ({ ...f, submitter_email: e.target.value }))}
              placeholder="you@example.com"
            />

            <Button
              className="w-full"
              disabled={!form.image}
              onClick={() => setStep('location')}
            >
              Next: Confirm location
            </Button>
          </div>
        )}

        {/* STEP 2: Location */}
        {step === 'location' && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <button onClick={() => setStep('photo')} className="text-gray-500 hover:text-gray-700">
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">Confirm location</h1>
                <p className="text-sm text-gray-500">Tap the map to pin the exact location</p>
              </div>
            </div>

            {gpsLoading && (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                Getting your location…
              </div>
            )}
            {gpsError && <Alert type="warning" message={gpsError} />}
            {form.lat && !gpsLoading && (
              <div className="flex items-center gap-2 text-xs text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-1.5">
                <MapPin className="w-3.5 h-3.5" />
                GPS: {form.lat.toFixed(5)}, {form.lng?.toFixed(5)}
                {form.location_accuracy && <span className="text-green-600 ml-1">(±{Math.round(form.location_accuracy)}m)</span>}
              </div>
            )}

            <LocationPickerMap
              lat={form.lat}
              lng={form.lng}
              onPick={(lat, lng) => setForm((f) => ({ ...f, lat, lng, location_source: f.location_source === 'gps' ? 'gps' : 'manual' }))}
            />

            <Input
              label="Address or landmark (optional)"
              value={form.address_hint}
              onChange={(e) => setForm((f) => ({ ...f, address_hint: e.target.value }))}
              placeholder="e.g. Near Gandhi Chowk, MG Road"
            />

            <div className="flex gap-3">
              <Button variant="secondary" onClick={() => setStep('photo')} className="flex-1">Back</Button>
              <Button onClick={() => setStep('review')} className="flex-1">Review &amp; Submit</Button>
            </div>
          </div>
        )}

        {/* STEP 3: Review */}
        {step === 'review' && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <button onClick={() => setStep('location')} className="text-gray-500 hover:text-gray-700">
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">Review your report</h1>
                <p className="text-sm text-gray-500">Check the details before submitting</p>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {form.imagePreview && (
                <img src={form.imagePreview} alt="Damage" className="w-full object-cover max-h-52" />
              )}
              <div className="p-4 space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-gray-500">Damage type</p>
                    <p className="font-medium text-gray-900 capitalize">{form.damage_type.replace(/_/g, ' ')}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Location</p>
                    <p className="font-medium text-gray-900">
                      {form.lat ? `${form.lat.toFixed(4)}, ${form.lng?.toFixed(4)}` : 'Not set'}
                    </p>
                  </div>
                </div>
                {form.description && (
                  <div>
                    <p className="text-xs text-gray-500">Description</p>
                    <p className="text-sm text-gray-700">{form.description}</p>
                  </div>
                )}
                {form.address_hint && (
                  <div>
                    <p className="text-xs text-gray-500">Address</p>
                    <p className="text-sm text-gray-700">{form.address_hint}</p>
                  </div>
                )}
              </div>
            </div>

            <Alert
              type="info"
              message="Your report will be reviewed by the road authority. AI analysis will run automatically."
            />

            <div className="flex gap-3">
              <Button variant="secondary" onClick={() => setStep('location')} className="flex-1">Back</Button>
              <Button loading={submitting} onClick={handleSubmit} className="flex-1">
                Submit report
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
