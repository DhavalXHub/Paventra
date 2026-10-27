import React from 'react';
import { Link } from 'react-router-dom';
import {
  Camera,
  Cpu,
  MapPin,
  Bell,
  Wrench,
  CheckCircle2,
  ArrowRight,
  Upload,
  ScanSearch,
  GitMerge,
  AlertTriangle,
  Users,
  BarChart3,
} from 'lucide-react';
import { PublicHeader } from '../components/PublicHeader';

const steps = [
  {
    number: '01',
    icon: Camera,
    title: 'Photograph the damage',
    description:
      'Open Paventra on any device — no app install required. Snap a photo of a pothole, crack, or damaged road surface directly from the browser.',
    detail:
      'Supported formats: JPEG, PNG, HEIC, WebP. Minimum recommended resolution 640 × 480 px. The system handles orientation correction automatically.',
    color: 'bg-amber-50 border-amber-200 text-amber-700',
    iconBg: 'bg-amber-100',
  },
  {
    number: '02',
    icon: MapPin,
    title: 'Pin the location',
    description:
      'Your device location is read automatically via the Geolocation API. Drag the map pin to correct it, or type an address for precision.',
    detail:
      'Coordinates are stored as WGS-84 latitude/longitude and displayed on the live damage map visible to coordinators.',
    color: 'bg-sky-50 border-sky-200 text-sky-700',
    iconBg: 'bg-sky-100',
  },
  {
    number: '03',
    icon: Upload,
    title: 'Submit the report',
    description:
      'Add optional context — road name, severity impression, access notes — then submit. You receive a unique tracking reference (e.g. PAV-XXXXXXXX) instantly.',
    detail:
      'Guest submissions are accepted. Registered citizens get persistent history and email notifications on status changes.',
    color: 'bg-violet-50 border-violet-200 text-violet-700',
    iconBg: 'bg-violet-100',
  },
  {
    number: '04',
    icon: ScanSearch,
    title: 'Computer-vision analysis',
    description:
      'A YOLO-based object-detection model inspects the uploaded image and identifies damage categories: longitudinal cracks, transverse cracks, alligator cracking, and potholes.',
    detail:
      'Detection runs server-side in milliseconds. Bounding-box confidence scores and damage-class labels are stored alongside the report.',
    color: 'bg-rose-50 border-rose-200 text-rose-700',
    iconBg: 'bg-rose-100',
  },
  {
    number: '05',
    icon: Cpu,
    title: 'Fuzzy severity scoring',
    description:
      'A 22-rule Mamdani Fuzzy Inference System interprets detection confidence, damage area, and road-context inputs to compute a continuous severity score (0–100) with linguistic labels.',
    detail:
      'The FIS handles the uncertainty inherent in real-world imagery. Unlike a binary classifier, it produces an explainable, graded output — "Moderate-High" rather than just "Damaged".',
    color: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    iconBg: 'bg-emerald-100',
  },
  {
    number: '06',
    icon: GitMerge,
    title: 'Deduplication & clustering',
    description:
      'Incoming reports are compared against existing open reports within a configurable spatial radius. Near-duplicates are linked, not created as independent records.',
    detail:
      'This prevents coordinators from being flooded with repeat submissions for the same pothole and ensures repair effort is consolidated.',
    color: 'bg-orange-50 border-orange-200 text-orange-700',
    iconBg: 'bg-orange-100',
  },
  {
    number: '07',
    icon: AlertTriangle,
    title: 'Priority ranking',
    description:
      'Reports are ranked by the fuzzy severity score, report frequency, and road classification. High-priority defects surface at the top of the coordinator dashboard.',
    detail:
      'The priority index updates dynamically as more reports arrive for the same location or as inspection results are entered.',
    color: 'bg-red-50 border-red-200 text-red-700',
    iconBg: 'bg-red-100',
  },
  {
    number: '08',
    icon: Users,
    title: 'Assignment & repair',
    description:
      'A road coordinator reviews the priority queue, inspects the evidence, and assigns a repair team with deadline and work-order notes.',
    detail:
      'Repair teams see their assigned jobs in a mobile-friendly work-order interface and can log completion photos and comments.',
    color: 'bg-indigo-50 border-indigo-200 text-indigo-700',
    iconBg: 'bg-indigo-100',
  },
  {
    number: '09',
    icon: Bell,
    title: 'Status notifications',
    description:
      'Citizens who submitted a report (or are tracking one) see real-time status changes: Submitted → Under Review → Assigned → In Progress → Resolved.',
    detail:
      'Each transition is timestamped. You can share the public tracking link with anyone — no account required to view status.',
    color: 'bg-teal-50 border-teal-200 text-teal-700',
    iconBg: 'bg-teal-100',
  },
  {
    number: '10',
    icon: BarChart3,
    title: 'Analytics & continuous improvement',
    description:
      'Big-data analytics aggregate detection patterns, repair durations, and geographic hotspots. Coordinators can benchmark AI performance and drill into fuzzy-system behavior.',
    detail:
      'The Soft Computing Inspector on the analytics page lets you run live Mamdani simulations, inspect rule activations, and read generated academic narratives.',
    color: 'bg-fuchsia-50 border-fuchsia-200 text-fuchsia-700',
    iconBg: 'bg-fuchsia-100',
  },
];

const faqs = [
  {
    q: 'Do I need to create an account to submit a report?',
    a: 'No. Guest submissions are fully supported. You will receive a tracking reference you can use to follow the repair progress without logging in.',
  },
  {
    q: 'How accurate is the AI damage detection?',
    a: 'The YOLO model is trained on the RDD2022 road damage dataset covering multiple countries. Confidence scores are always shown transparently. A low-confidence detection is flagged for human review rather than auto-accepted.',
  },
  {
    q: 'What happens when the same pothole is reported multiple times?',
    a: 'The deduplication engine clusters geographically proximate open reports and links them. Each linked report increases the priority score, so frequently-reported damage rises faster in the queue.',
  },
  {
    q: 'How is repair urgency decided?',
    a: 'A 22-rule Fuzzy Inference System maps detection confidence, damage area, and road-class inputs onto a continuous severity score. This score, combined with report frequency, determines the coordinator priority queue. The system is explainable — every score comes with a linguistic rationale.',
  },
  {
    q: 'Can I track a report submitted by someone else?',
    a: 'Yes. The tracking reference (e.g. PAV-L3V5ATC5) is public. Anyone with the reference can view the current status, timeline, and resolution notes.',
  },
  {
    q: 'Who acts on the reports?',
    a: 'Verified road coordinators — municipal engineers with a Coordinator role — review the priority queue, conduct inspections, and dispatch repair teams. Coordinators access a dedicated portal with a live map, analytics, and team-management tools.',
  },
];

export default function HowItWorksPage() {
  return (
    <div className="min-h-screen bg-[#fafaf8] flex flex-col">
      <PublicHeader current="home" />

      {/* Hero */}
      <section className="bg-[#14462a] text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-sm font-medium mb-6">
            <CheckCircle2 className="w-4 h-4" />
            <span>End-to-end workflow</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            How Paventra works
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto">
            From a single photograph to a completed repair — ten transparent steps powered by
            computer vision, fuzzy logic, and real-time collaboration.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to="/report"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white text-[#14462a] font-semibold text-sm hover:bg-stone-100 transition-colors"
            >
              Report road damage <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/track"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-white/40 text-white font-semibold text-sm hover:bg-white/10 transition-colors"
            >
              Track a report
            </Link>
          </div>
        </div>
      </section>

      {/* Steps */}
      <section className="py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-stone-900 mb-2 text-center">The 10-step pipeline</h2>
          <p className="text-stone-500 text-center mb-12">
            Every report moves through the same transparent, AI-assisted pipeline.
          </p>

          <div className="space-y-6">
            {steps.map((step) => {
              const Icon = step.icon;
              return (
                <div
                  key={step.number}
                  className={`flex gap-5 p-6 rounded-2xl border ${step.color} bg-opacity-40`}
                >
                  <div
                    className={`flex-shrink-0 w-12 h-12 rounded-xl ${step.iconBg} flex items-center justify-center`}
                  >
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-xs font-bold tracking-widest text-stone-400 uppercase">
                        Step {step.number}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-stone-900 mb-1">{step.title}</h3>
                    <p className="text-stone-700 mb-2">{step.description}</p>
                    <p className="text-sm text-stone-500">{step.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-4 bg-stone-50 border-t border-stone-200">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-stone-900 mb-8 text-center">
            Frequently asked questions
          </h2>
          <div className="space-y-5">
            {faqs.map((faq, i) => (
              <div key={i} className="bg-white rounded-xl border border-stone-200 p-5">
                <h3 className="font-semibold text-stone-900 mb-2">{faq.q}</h3>
                <p className="text-stone-600 text-sm leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-14 px-4 bg-[#14462a]">
        <div className="max-w-2xl mx-auto text-center text-white">
          <h2 className="text-2xl font-bold mb-3">Ready to report road damage?</h2>
          <p className="text-white/75 mb-6">
            No account required. Submit in under two minutes.
          </p>
          <Link
            to="/report"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-white text-[#14462a] font-semibold hover:bg-stone-100 transition-colors"
          >
            Get started <ArrowRight className="w-4 h-4" />
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
