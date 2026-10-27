import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Send,
  Search,
  ClipboardList,
  Wrench,
  CheckCircle2,
  Clock,
  ArrowRight,
  ChevronRight,
  Info,
  Star,
  AlertCircle,
} from 'lucide-react';
import { PublicHeader } from '../components/PublicHeader';

type StageId = 'submitted' | 'under_review' | 'assigned' | 'in_progress' | 'resolved' | 'rejected' | 'duplicate';

interface Stage {
  id: StageId;
  label: string;
  icon: React.ElementType;
  color: string;
  bg: string;
  border: string;
  badgeBg: string;
  description: string;
  whoActs: string;
  typicalDuration: string;
  transitions: { to: StageId; condition: string }[];
  citizenAction: string;
  coordinatorAction: string;
}

const stages: Stage[] = [
  {
    id: 'submitted',
    label: 'Submitted',
    icon: Send,
    color: 'text-sky-700',
    bg: 'bg-sky-50',
    border: 'border-sky-300',
    badgeBg: 'bg-sky-100 text-sky-700',
    description:
      'A citizen or guest has uploaded a photo, pinned a location, and submitted the report. The AI pipeline (computer vision + fuzzy scoring) runs immediately and a tracking reference is issued.',
    whoActs: 'System (automated)',
    typicalDuration: 'Seconds to minutes',
    transitions: [
      { to: 'under_review', condition: 'AI scoring completes and the report enters the coordinator queue' },
      { to: 'duplicate', condition: 'Deduplication finds an existing open report within 50 m' },
    ],
    citizenAction: 'Receive tracking reference (e.g. PAV-XXXXXXXX). Share or bookmark it.',
    coordinatorAction: 'Report appears in the priority queue after AI processing.',
  },
  {
    id: 'under_review',
    label: 'Under Review',
    icon: Search,
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    border: 'border-amber-300',
    badgeBg: 'bg-amber-100 text-amber-700',
    description:
      'A coordinator is actively reviewing the evidence, the AI detection results, the fuzzy severity score, and any related linked reports. They may request an on-site inspection.',
    whoActs: 'Road Coordinator',
    typicalDuration: '1 – 3 business days',
    transitions: [
      { to: 'assigned', condition: 'Coordinator confirms severity and assigns a repair team' },
      { to: 'rejected', condition: 'Report is invalid, out of jurisdiction, or cannot be verified' },
      { to: 'duplicate', condition: 'Manual review reveals an existing job covers the same defect' },
    ],
    citizenAction: 'No action required. Check status anytime with your tracking reference.',
    coordinatorAction: 'Inspect AI results, view on map, cross-check duplicates, decide next action.',
  },
  {
    id: 'assigned',
    label: 'Assigned',
    icon: ClipboardList,
    color: 'text-violet-700',
    bg: 'bg-violet-50',
    border: 'border-violet-300',
    badgeBg: 'bg-violet-100 text-violet-700',
    description:
      'A repair team has been formally assigned to this report. They have received a work order with location, damage type, severity score, and any coordinator notes. A target completion date is set.',
    whoActs: 'Repair Team (receives work order)',
    typicalDuration: '1 – 7 days (before work begins)',
    transitions: [
      { to: 'in_progress', condition: 'Repair team acknowledges and begins work on site' },
    ],
    citizenAction: 'Status change is visible via tracking reference.',
    coordinatorAction: 'Monitor assignment; can re-assign if team is unavailable.',
  },
  {
    id: 'in_progress',
    label: 'In Progress',
    icon: Wrench,
    color: 'text-orange-700',
    bg: 'bg-orange-50',
    border: 'border-orange-300',
    badgeBg: 'bg-orange-100 text-orange-700',
    description:
      'Active repair work is underway at the reported location. The repair team can log progress notes and upload completion photos directly from their mobile interface.',
    whoActs: 'Repair Team',
    typicalDuration: 'Hours to days depending on severity',
    transitions: [
      { to: 'resolved', condition: 'Repair team marks work as complete and uploads verification photo' },
    ],
    citizenAction: 'Track progress. Optionally submit additional evidence if damage worsens.',
    coordinatorAction: 'Monitor in-field progress; can escalate priority or adjust deadline.',
  },
  {
    id: 'resolved',
    label: 'Resolved',
    icon: CheckCircle2,
    color: 'text-emerald-700',
    bg: 'bg-emerald-50',
    border: 'border-emerald-300',
    badgeBg: 'bg-emerald-100 text-emerald-700',
    description:
      'The defect has been repaired and the report is closed. A resolution timestamp and optional completion notes are recorded. The repair data feeds into the analytics engine.',
    whoActs: 'System (closed by coordinator / repair team)',
    typicalDuration: 'Terminal state',
    transitions: [],
    citizenAction: 'View resolution details and timeline on the tracking page. Rate the repair if prompted.',
    coordinatorAction: 'Verified closure. Data contributes to repair-time benchmarks and analytics.',
  },
  {
    id: 'duplicate',
    label: 'Duplicate',
    icon: Info,
    color: 'text-stone-600',
    bg: 'bg-stone-50',
    border: 'border-stone-300',
    badgeBg: 'bg-stone-100 text-stone-600',
    description:
      'This report has been linked to an existing open report for the same defect. It is not discarded — it increases the priority score of the parent report instead.',
    whoActs: 'System (automated deduplication) or Coordinator (manual merge)',
    typicalDuration: 'Resolves when parent closes',
    transitions: [
      { to: 'resolved', condition: 'Parent report is resolved; all linked duplicates auto-close' },
    ],
    citizenAction: 'Your tracking reference still works. You will see the parent\'s status and timeline.',
    coordinatorAction: 'Linked reports visible in parent detail. Duplicate count boosts priority score.',
  },
  {
    id: 'rejected',
    label: 'Rejected',
    icon: AlertCircle,
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-300',
    badgeBg: 'bg-red-100 text-red-700',
    description:
      'The report was reviewed and determined to be invalid: the image does not show road damage, the location is outside the jurisdiction, the submission violates content policy, or the damage cannot be verified.',
    whoActs: 'Coordinator',
    typicalDuration: 'Terminal state',
    transitions: [],
    citizenAction: 'Rejection reason is visible on the tracking page. You may file a new report with corrected information.',
    coordinatorAction: 'Record rejection reason for audit trail. Citizen is notified via tracking page.',
  },
];

const stageOrder: StageId[] = ['submitted', 'under_review', 'assigned', 'in_progress', 'resolved'];

export default function LifecyclePage() {
  const [selected, setSelected] = useState<StageId>('submitted');
  const stage = stages.find((s) => s.id === selected)!;
  const Icon = stage.icon;

  return (
    <div className="min-h-screen bg-[#fafaf8] flex flex-col">
      <PublicHeader current="home" />

      {/* Hero */}
      <section className="bg-[#14462a] text-white py-20 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-sm font-medium mb-6">
            <Clock className="w-4 h-4" />
            <span>7-state lifecycle</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            Report lifecycle
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto">
            Every Paventra report follows a transparent, audited state machine — from first
            submission to verified repair. Explore each stage below.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              to="/report"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white text-[#14462a] font-semibold text-sm hover:bg-stone-100 transition-colors"
            >
              Submit a report <ArrowRight className="w-4 h-4" />
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

      {/* Main flow diagram (linear) */}
      <section className="py-14 px-4">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-xl font-bold text-stone-900 mb-2 text-center">
            Primary resolution path
          </h2>
          <p className="text-stone-500 text-sm text-center mb-8">
            Most reports follow this path. Click any stage for details. Branch states (Duplicate, Rejected) are below.
          </p>

          {/* Linear stage flow */}
          <div className="flex flex-wrap items-center justify-center gap-2 mb-10">
            {stageOrder.map((id, i) => {
              const s = stages.find((st) => st.id === id)!;
              const SIcon = s.icon;
              const isActive = selected === id;
              return (
                <React.Fragment key={id}>
                  <button
                    onClick={() => setSelected(id)}
                    className={`flex flex-col items-center px-4 py-3 rounded-xl border transition-all text-center min-w-[100px] ${
                      isActive
                        ? `${s.bg} ${s.border} ${s.color} shadow-md scale-105`
                        : 'bg-white border-stone-200 text-stone-600 hover:border-stone-300 hover:shadow-sm'
                    }`}
                  >
                    <SIcon className={`w-5 h-5 mb-1 ${isActive ? s.color : 'text-stone-500'}`} />
                    <span className="text-xs font-semibold whitespace-nowrap">{s.label}</span>
                  </button>
                  {i < stageOrder.length - 1 && (
                    <ChevronRight className="w-5 h-5 text-stone-300 flex-shrink-0" />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Branch states */}
          <div className="flex flex-wrap justify-center gap-3 mb-12">
            {['duplicate', 'rejected'].map((id) => {
              const s = stages.find((st) => st.id === id)!;
              const SIcon = s.icon;
              const isActive = selected === id;
              return (
                <button
                  key={id}
                  onClick={() => setSelected(id as StageId)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all text-sm font-semibold ${
                    isActive
                      ? `${s.bg} ${s.border} ${s.color} shadow-sm`
                      : 'bg-white border-stone-200 text-stone-500 hover:border-stone-300'
                  }`}
                >
                  <SIcon className="w-4 h-4" />
                  {s.label} <span className="text-xs font-normal">(branch)</span>
                </button>
              );
            })}
          </div>

          {/* Stage detail card */}
          <div className={`rounded-2xl border p-8 ${stage.bg} ${stage.border} transition-all`}>
            <div className="flex items-start gap-5 flex-wrap">
              <div className="w-12 h-12 rounded-xl bg-white/70 flex items-center justify-center flex-shrink-0">
                <Icon className={`w-6 h-6 ${stage.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 flex-wrap mb-1">
                  <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${stage.badgeBg}`}>
                    {stage.label}
                  </span>
                  <span className="text-xs text-stone-500 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> {stage.typicalDuration}
                  </span>
                </div>
                <p className={`text-xs font-semibold uppercase tracking-widest mb-2 ${stage.color}`}>
                  Acting party: {stage.whoActs}
                </p>
                <p className="text-stone-700 mb-6 leading-relaxed">{stage.description}</p>

                <div className="grid sm:grid-cols-2 gap-4 mb-6">
                  <div className="bg-white/70 rounded-xl p-4 border border-stone-100">
                    <p className="text-xs font-bold text-stone-500 uppercase tracking-wider mb-2">
                      Citizen perspective
                    </p>
                    <p className="text-sm text-stone-700">{stage.citizenAction}</p>
                  </div>
                  <div className="bg-white/70 rounded-xl p-4 border border-stone-100">
                    <p className="text-xs font-bold text-stone-500 uppercase tracking-wider mb-2">
                      Coordinator perspective
                    </p>
                    <p className="text-sm text-stone-700">{stage.coordinatorAction}</p>
                  </div>
                </div>

                {stage.transitions.length > 0 && (
                  <div>
                    <p className="text-xs font-bold text-stone-500 uppercase tracking-wider mb-3">
                      Possible transitions
                    </p>
                    <div className="flex flex-col gap-2">
                      {stage.transitions.map((t) => {
                        const target = stages.find((s) => s.id === t.to)!;
                        const TIcon = target.icon;
                        return (
                          <button
                            key={t.to}
                            onClick={() => setSelected(t.to)}
                            className="flex items-start gap-3 text-left group"
                          >
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold flex-shrink-0 ${target.badgeBg}`}
                            >
                              <TIcon className="w-3 h-3" /> {target.label}
                            </span>
                            <span className="text-sm text-stone-600 group-hover:text-stone-900 transition-colors">
                              {t.condition}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {stage.transitions.length === 0 && (
                  <div className="flex items-center gap-2 text-sm text-stone-500">
                    <Star className="w-4 h-4" />
                    <span>This is a terminal state. No further transitions occur.</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* SLA reference table */}
      <section className="py-14 px-4 bg-stone-50 border-t border-stone-200">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xl font-bold text-stone-900 mb-6 text-center">
            Stage reference
          </h2>
          <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-stone-100 bg-stone-50">
                  <th className="text-left px-4 py-3 font-semibold text-stone-600 text-xs uppercase tracking-wider">Stage</th>
                  <th className="text-left px-4 py-3 font-semibold text-stone-600 text-xs uppercase tracking-wider">Acting party</th>
                  <th className="text-left px-4 py-3 font-semibold text-stone-600 text-xs uppercase tracking-wider">Typical duration</th>
                  <th className="text-left px-4 py-3 font-semibold text-stone-600 text-xs uppercase tracking-wider">Terminal?</th>
                </tr>
              </thead>
              <tbody>
                {stages.map((s, i) => {
                  const SIcon = s.icon;
                  return (
                    <tr
                      key={s.id}
                      className={`border-b border-stone-100 hover:bg-stone-50 cursor-pointer transition-colors ${
                        i === stages.length - 1 ? 'border-none' : ''
                      }`}
                      onClick={() => setSelected(s.id)}
                    >
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${s.badgeBg}`}>
                          <SIcon className="w-3 h-3" /> {s.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-stone-600">{s.whoActs}</td>
                      <td className="px-4 py-3 text-stone-600">{s.typicalDuration}</td>
                      <td className="px-4 py-3">
                        {s.transitions.length === 0 ? (
                          <span className="text-xs font-semibold text-emerald-700">Yes</span>
                        ) : (
                          <span className="text-xs text-stone-400">No</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-14 px-4 bg-[#14462a]">
        <div className="max-w-2xl mx-auto text-center text-white">
          <h2 className="text-2xl font-bold mb-3">See your report's lifecycle in real time</h2>
          <p className="text-white/75 mb-6">
            Submit a report or paste your tracking reference to follow every state transition live.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              to="/report"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white text-[#14462a] font-semibold text-sm hover:bg-stone-100 transition-colors"
            >
              Report damage <ArrowRight className="w-4 h-4" />
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
