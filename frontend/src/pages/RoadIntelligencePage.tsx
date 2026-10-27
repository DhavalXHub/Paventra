import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Brain,
  Eye,
  BarChart3,
  Map,
  ArrowRight,
  CheckCircle2,
  Zap,
  Activity,
  Layers,
  Database,
  GitBranch,
  FlaskConical,
  Shield,
  Globe,
} from 'lucide-react';
import { PublicHeader } from '../components/PublicHeader';

const pillars = [
  {
    id: 'cv',
    icon: Eye,
    label: 'Computer Vision',
    title: 'YOLO-based damage detection',
    color: 'text-sky-700',
    bg: 'bg-sky-50',
    border: 'border-sky-200',
    accent: '#0369a1',
    points: [
      'Real-time object detection using a YOLO architecture fine-tuned on the RDD2022 road damage dataset.',
      'Detects four damage categories: longitudinal cracks, transverse cracks, alligator cracking, and potholes.',
      'Each detected bounding box carries a confidence score used as a direct input to the fuzzy engine.',
      'Damage area percentage is estimated from bounding-box geometry relative to image dimensions.',
      'Sub-second inference on server hardware; images are never stored longer than necessary.',
    ],
    tech: ['YOLO', 'PyTorch', 'OpenCV', 'RDD2022 dataset', 'FastAPI inference endpoint'],
  },
  {
    id: 'sc',
    icon: Brain,
    label: 'Soft Computing',
    title: 'Mamdani Fuzzy Inference System',
    color: 'text-emerald-700',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    accent: '#047857',
    points: [
      '22-rule complete Mamdani FIS with three antecedent variables: detection confidence, damage area, and road classification.',
      'Trapezoidal and triangular membership functions partition each input into linguistic labels (e.g., Low / Medium / High).',
      'Consequent variable — repair priority — is defuzzified using centroid-of-gravity to yield a continuous 0–100 score.',
      'Rule activations and membership degrees are logged, making every score fully explainable and auditable.',
      'Thread-safe per-invocation simulation: each report gets an independent fuzzy computation with no shared state.',
      'An academic narrative is auto-generated from the dominant activated rules and presented alongside the score.',
    ],
    tech: [
      'skfuzzy (scikit-fuzzy)',
      'NumPy',
      'Mamdani inference',
      'Centroid defuzzification',
      '22-rule base',
    ],
  },
  {
    id: 'analytics',
    icon: BarChart3,
    label: 'Big Data Analytics',
    title: 'Scale-aware pattern intelligence',
    color: 'text-violet-700',
    bg: 'bg-violet-50',
    border: 'border-violet-200',
    accent: '#6d28d9',
    points: [
      'Aggregates detection events, report lifecycle transitions, and repair outcomes across all historical records.',
      'Hotspot clustering identifies road segments with recurring damage using spatial density analysis.',
      'Trend analytics surface degradation rates: which road classes deteriorate fastest between maintenance cycles.',
      'A 250-record soft-computing benchmark evaluates FIS output distributions and identifies edge-case inputs.',
      'Coordinator analytics page embeds the live Soft Computing Inspector for real-time FIS interrogation.',
    ],
    tech: [
      'Pandas',
      'SQLAlchemy aggregations',
      'GeoJSON clustering',
      'TanStack Query',
      'Recharts visualizations',
    ],
  },
  {
    id: 'geo',
    icon: Map,
    label: 'Geospatial',
    title: 'Live damage map & deduplication',
    color: 'text-rose-700',
    bg: 'bg-rose-50',
    border: 'border-rose-200',
    accent: '#be123c',
    points: [
      'Every report is pinned to WGS-84 coordinates captured from device GPS or manual map selection.',
      'The coordinator map renders all open reports as severity-colored markers with popup detail panels.',
      'Haversine-distance deduplication clusters new submissions within a configurable radius (default 50 m).',
      'Duplicate reports boost the priority score of the parent record instead of creating noise.',
      'Heatmap overlays let coordinators identify high-incident corridors at a glance.',
    ],
    tech: ['Leaflet.js / React-Leaflet', 'Haversine distance', 'GeoJSON', 'PostGIS-ready schema'],
  },
];

const benchmarkStats = [
  { label: 'Training images (RDD2022)', value: '~47,000' },
  { label: 'Damage categories', value: '4' },
  { label: 'FIS rules', value: '22' },
  { label: 'Antecedent variables', value: '3' },
  { label: 'Benchmark records', value: '250' },
  { label: 'Backend test coverage', value: '49 tests' },
];

export default function RoadIntelligencePage() {
  const [active, setActive] = useState('cv');
  const activePillar = pillars.find((p) => p.id === active)!;
  const Icon = activePillar.icon;

  return (
    <div className="min-h-screen bg-[#fafaf8] flex flex-col">
      <PublicHeader current="home" />

      {/* Hero */}
      <section className="bg-[#14462a] text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-sm font-medium mb-6">
            <Brain className="w-4 h-4" />
            <span>AI · Soft Computing · Analytics · Geospatial</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Road Intelligence
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto">
            Paventra integrates four technical pillars to transform a single road photograph
            into an explainable, prioritized repair signal.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to="/report"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white text-[#14462a] font-semibold text-sm hover:bg-stone-100 transition-colors"
            >
              Try it now <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/how-it-works"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-white/40 text-white font-semibold text-sm hover:bg-white/10 transition-colors"
            >
              See the workflow
            </Link>
          </div>
        </div>
      </section>

      {/* Four-pillar tabs */}
      <section className="py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-stone-900 mb-2 text-center">
            Four integrated pillars
          </h2>
          <p className="text-stone-500 text-center mb-10">
            Click a pillar to explore the technology.
          </p>

          {/* Tab bar */}
          <div className="flex flex-wrap gap-3 justify-center mb-10">
            {pillars.map((p) => {
              const PIcon = p.icon;
              return (
                <button
                  key={p.id}
                  onClick={() => setActive(p.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border font-semibold text-sm transition-all ${
                    active === p.id
                      ? `${p.bg} ${p.border} ${p.color} shadow-sm`
                      : 'bg-white border-stone-200 text-stone-600 hover:border-stone-300'
                  }`}
                >
                  <PIcon className="w-4 h-4" />
                  {p.label}
                </button>
              );
            })}
          </div>

          {/* Active pillar detail */}
          <div
            className={`rounded-2xl border p-8 ${activePillar.bg} ${activePillar.border} transition-all`}
          >
            <div className="flex items-start gap-5">
              <div className="w-12 h-12 rounded-xl bg-white/70 flex items-center justify-center flex-shrink-0">
                <Icon className={`w-6 h-6 ${activePillar.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs font-bold uppercase tracking-widest mb-1 ${activePillar.color}`}>
                  {activePillar.label}
                </p>
                <h3 className="text-2xl font-bold text-stone-900 mb-5">
                  {activePillar.title}
                </h3>
                <ul className="space-y-3 mb-6">
                  {activePillar.points.map((pt, i) => (
                    <li key={i} className="flex items-start gap-3 text-stone-700">
                      <CheckCircle2 className={`w-4 h-4 mt-0.5 flex-shrink-0 ${activePillar.color}`} />
                      <span className="text-sm leading-relaxed">{pt}</span>
                    </li>
                  ))}
                </ul>
                <div>
                  <p className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-2">
                    Technologies
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {activePillar.tech.map((t) => (
                      <span
                        key={t}
                        className="px-2.5 py-1 rounded-md bg-white/80 border border-stone-200 text-xs font-medium text-stone-700"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* System statistics */}
      <section className="py-14 px-4 bg-stone-50 border-t border-stone-200">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xl font-bold text-stone-900 mb-8 text-center">
            System at a glance
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {benchmarkStats.map((s) => (
              <div
                key={s.label}
                className="bg-white rounded-xl border border-stone-200 p-5 text-center"
              >
                <div className="text-2xl font-bold text-[#14462a] mb-1">{s.value}</div>
                <div className="text-xs text-stone-500">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture diagram (text-based) */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xl font-bold text-stone-900 mb-2 text-center">
            Data flow overview
          </h2>
          <p className="text-stone-500 text-center mb-10 text-sm">
            From citizen upload to coordinator action in one continuous pipeline.
          </p>

          <div className="flex flex-col sm:flex-row items-stretch gap-0">
            {[
              { label: 'Citizen Upload', icon: Globe, color: 'bg-sky-100 text-sky-700 border-sky-200' },
              { label: 'CV Detection', icon: Eye, color: 'bg-amber-100 text-amber-700 border-amber-200' },
              { label: 'Fuzzy FIS', icon: Brain, color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
              { label: 'Priority Queue', icon: Zap, color: 'bg-rose-100 text-rose-700 border-rose-200' },
              { label: 'Coordinator', icon: Shield, color: 'bg-violet-100 text-violet-700 border-violet-200' },
              { label: 'Analytics', icon: BarChart3, color: 'bg-stone-100 text-stone-700 border-stone-200' },
            ].map((step, i, arr) => {
              const StepIcon = step.icon;
              return (
                <React.Fragment key={step.label}>
                  <div
                    className={`flex-1 flex flex-col items-center justify-center p-4 rounded-xl border ${step.color} text-center`}
                  >
                    <StepIcon className="w-6 h-6 mb-2" />
                    <span className="text-xs font-semibold">{step.label}</span>
                  </div>
                  {i < arr.length - 1 && (
                    <div className="flex items-center justify-center px-1 text-stone-300 font-bold text-lg select-none">
                      →
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </section>

      {/* Explainability callout */}
      <section className="py-14 px-4 bg-[#14462a]/5 border-t border-[#14462a]/10">
        <div className="max-w-3xl mx-auto text-center">
          <FlaskConical className="w-10 h-10 text-[#14462a] mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-stone-900 mb-3">
            Built for academic rigour &amp; practical trust
          </h2>
          <p className="text-stone-600 mb-6 leading-relaxed">
            Every AI decision in Paventra is explainable. The fuzzy engine logs which rules
            activated, what membership degrees each input achieved, and how the centroid defuzzification
            arrived at the final score. Coordinators see a plain-English narrative alongside every
            severity badge.
          </p>
          <Link
            to="/coordinator/analytics"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#14462a] text-white font-semibold text-sm hover:bg-[#0f3620] transition-colors"
          >
            Open the Soft Computing Inspector <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-stone-200 py-6 px-4 bg-white text-center text-xs text-stone-400">
        © {new Date().getFullYear()} Paventra — Road Damage Intelligence. All rights reserved.
        <span className="mx-2">·</span>
        <Link to="/how-it-works" className="hover:text-stone-600">How it works</Link>
        <span className="mx-2">·</span>
        <Link to="/road-intelligence" className="hover:text-stone-600">Road Intelligence</Link>
        <span className="mx-2">·</span>
        <Link to="/lifecycle" className="hover:text-stone-600">Lifecycle</Link>
      </footer>
    </div>
  );
}
