import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '../lib/api';
import { Card, CardHeader, CardTitle } from './Card';
import { Cpu, Sliders, BookOpen, Database, Sparkles, AlertTriangle, ArrowUpRight, ArrowDownRight, CheckCircle2 } from 'lucide-react';

interface SimulationResult {
  priority_score: number;
  priority_label: string;
  engine_used: string;
  baseline_score: number;
  decision_delta: number;
  top_contributing_factors: Array<{ factor: string; weight: string; value: number }>;
  membership_activations: Record<string, Record<string, number>>;
  explanation_narrative: string;
  inputs: Record<string, number>;
}

interface BenchmarkResponse {
  total_records: number;
  summary: {
    average_fuzzy_priority: number;
    average_baseline_score: number;
    critical_reports: number;
    high_reports: number;
    cases_elevated_by_fuzzy: number;
    cases_subdued_by_fuzzy: number;
  };
  records_sample: Array<{
    public_ref: string;
    class_description: string;
    provisional_severity_score: number;
    traffic_exposure_score: number;
    time_unresolved_days: number;
    safety_urgency_score: number;
    fuzzy_priority_score: number;
    baseline_weighted_score: number;
    decision_delta: number;
    priority_label: string;
    road_segment: string;
  }>;
}

const PRESETS = [
  {
    name: '🚨 School Zone Pothole',
    desc: 'High severity + high pedestrian safety urgency',
    values: { severity: 8.5, traffic_exposure: 8.5, time_unresolved_days: 12, safety_urgency: 9.5 },
  },
  {
    name: '⏳ Neglected Rural Crack',
    desc: 'Low/mod severity + unresolved for 180+ days',
    values: { severity: 3.8, traffic_exposure: 2.5, time_unresolved_days: 180, safety_urgency: 3.5 },
  },
  {
    name: '🚗 Heavy Highway Fatigue',
    desc: 'Moderate alligator crack on arterial freight route',
    values: { severity: 6.2, traffic_exposure: 9.5, time_unresolved_days: 30, safety_urgency: 7.5 },
  },
  {
    name: '🏡 Suburban Minor Wear',
    desc: 'Low severity + low traffic + recent report',
    values: { severity: 2.2, traffic_exposure: 3.0, time_unresolved_days: 4, safety_urgency: 2.0 },
  },
];

export function SoftComputingInspector() {
  const [activeTab, setActiveTab] = useState<'simulator' | 'rules' | 'benchmark'>('simulator');
  const [inputs, setInputs] = useState({
    severity: 7.5,
    traffic_exposure: 8.0,
    time_unresolved_days: 28,
    safety_urgency: 8.5,
  });

  // Query metadata
  const { data: metadata } = useQuery({
    queryKey: ['fuzzy-metadata'],
    queryFn: () => api.get('/analytics/fuzzy-metadata').then((r) => r.data),
    staleTime: 600000,
  });

  // Query benchmark
  const { data: benchmarkData } = useQuery<BenchmarkResponse>({
    queryKey: ['fuzzy-benchmark'],
    queryFn: () => api.get('/analytics/soft-computing-benchmark').then((r) => r.data),
    staleTime: 600000,
  });

  // Real-time simulate query / mutation
  const simulateMutation = useMutation({
    mutationFn: (vals: typeof inputs) => api.post('/analytics/fuzzy-simulate', vals).then((r) => r.data),
  });

  const [simResult, setSimResult] = useState<SimulationResult | null>(null);

  // Trigger initial simulation
  React.useEffect(() => {
    let isCurrent = true;
    api.post('/analytics/fuzzy-simulate', inputs)
      .then((r) => {
        if (isCurrent) setSimResult(r.data);
      })
      .catch(() => {});
    return () => { isCurrent = false; };
  }, [inputs]);

  function handleSliderChange(key: keyof typeof inputs, val: number) {
    const updated = { ...inputs, [key]: val };
    setInputs(updated);
  }

  function handlePreset(p: typeof PRESETS[0]) {
    setInputs(p.values);
  }

  const score = simResult?.priority_score ?? 0;
  const baseline = simResult?.baseline_score ?? 0;
  const delta = simResult?.decision_delta ?? 0;
  const label = simResult?.priority_label ?? 'MODERATE';

  const badgeColor =
    label === 'CRITICAL'
      ? 'bg-red-100 text-red-800 border-red-300'
      : label === 'HIGH'
      ? 'bg-amber-100 text-amber-800 border-amber-300'
      : label === 'MEDIUM_HIGH'
      ? 'bg-yellow-100 text-yellow-800 border-yellow-300'
      : label === 'MEDIUM'
      ? 'bg-blue-100 text-blue-800 border-blue-300'
      : 'bg-green-100 text-green-800 border-green-300';

  return (
    <Card className="border-accent/30 shadow-sm overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-stone-900 to-stone-800 text-white rounded-t-lg p-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center text-accent">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-white text-base">Soft Computing: Mamdani Fuzzy Inference System</CardTitle>
              <p className="text-xs text-stone-300 mt-0.5">
                Explainable non-linear repair prioritization under uncertainty (22 Rule Base · Centroid Defuzzification)
              </p>
            </div>
          </div>

          {/* Tab selectors */}
          <div className="flex rounded-lg bg-stone-950/60 p-1 border border-stone-700/60 text-xs">
            <button
              onClick={() => setActiveTab('simulator')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-all ${
                activeTab === 'simulator'
                  ? 'bg-accent text-white shadow-sm'
                  : 'text-stone-300 hover:text-white'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              Simulator
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-all ${
                activeTab === 'rules'
                  ? 'bg-accent text-white shadow-sm'
                  : 'text-stone-300 hover:text-white'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              Rule Base (22)
            </button>
            <button
              onClick={() => setActiveTab('benchmark')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-all ${
                activeTab === 'benchmark'
                  ? 'bg-accent text-white shadow-sm'
                  : 'text-stone-300 hover:text-white'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              Benchmark (250)
            </button>
          </div>
        </div>
      </CardHeader>

      <div className="p-5">
        {/* TAB 1: INTERACTIVE SIMULATOR */}
        {activeTab === 'simulator' && (
          <div className="space-y-6">
            {/* Presets row */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Academic Test Scenarios</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                {PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => handlePreset(p)}
                    className="text-left p-2.5 rounded-md border border-gray-200 bg-gray-50 hover:bg-accent/5 hover:border-accent/40 transition-all text-xs"
                  >
                    <p className="font-semibold text-gray-900">{p.name}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5">{p.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Sliders (7 cols) */}
              <div className="lg:col-span-7 space-y-4 bg-gray-50/70 p-4 rounded-lg border border-gray-200">
                <p className="text-xs font-bold text-gray-700 uppercase tracking-wider">Mamdani Antecedent Inputs</p>

                {/* Severity */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-gray-700">1. Damage Severity (Estimated 2D Footprint)</span>
                    <span className="font-mono font-bold text-accent">{inputs.severity.toFixed(1)} / 10.0</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.1"
                    value={inputs.severity}
                    onChange={(e) => handleSliderChange('severity', parseFloat(e.target.value))}
                    className="w-full accent-accent h-1.5 bg-gray-200 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-gray-400">
                    <span>Low (0-4)</span>
                    <span>Moderate (2-8)</span>
                    <span>High (6-10)</span>
                    <span>Critical (8.5-10)</span>
                  </div>
                </div>

                {/* Traffic */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-gray-700">2. Traffic Exposure (Road Hierarchy Index)</span>
                    <span className="font-mono font-bold text-accent">{inputs.traffic_exposure.toFixed(1)} / 10.0</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.1"
                    value={inputs.traffic_exposure}
                    onChange={(e) => handleSliderChange('traffic_exposure', parseFloat(e.target.value))}
                    className="w-full accent-accent h-1.5 bg-gray-200 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-gray-400">
                    <span>Low Traffic (0-4)</span>
                    <span>Medium Traffic (2-8)</span>
                    <span>Heavy Arterial / Highway (6-10)</span>
                  </div>
                </div>

                {/* Time Unresolved */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-gray-700">3. Time Pending Resolution</span>
                    <span className="font-mono font-bold text-accent">{Math.round(inputs.time_unresolved_days)} days</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="365"
                    step="1"
                    value={inputs.time_unresolved_days}
                    onChange={(e) => handleSliderChange('time_unresolved_days', parseInt(e.target.value, 10))}
                    className="w-full accent-accent h-1.5 bg-gray-200 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-gray-400">
                    <span>Short (0-30d)</span>
                    <span>Medium (14-120d)</span>
                    <span>Long (60-200d)</span>
                    <span>Very Long (150-365d)</span>
                  </div>
                </div>

                {/* Safety Urgency */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-gray-700">4. Safety Hazard / Pedestrian Urgency</span>
                    <span className="font-mono font-bold text-accent">{inputs.safety_urgency.toFixed(1)} / 10.0</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="10"
                    step="0.1"
                    value={inputs.safety_urgency}
                    onChange={(e) => handleSliderChange('safety_urgency', parseFloat(e.target.value))}
                    className="w-full accent-accent h-1.5 bg-gray-200 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-gray-400">
                    <span>Low Risk (0-4)</span>
                    <span>Medium (2-8)</span>
                    <span>High Danger Zone (6-10)</span>
                  </div>
                </div>
              </div>

              {/* Output & Explainability (5 cols) */}
              <div className="lg:col-span-5 space-y-4">
                {/* Result Card */}
                <div className="p-4 rounded-lg border border-gray-200 bg-white shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Defuzzified Priority</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeColor}`}>
                      {label}
                    </span>
                  </div>

                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-extrabold text-gray-900 font-mono tracking-tight">
                      {score.toFixed(1)}
                    </span>
                    <span className="text-sm text-gray-500 font-medium">/ 100</span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        score >= 85 ? 'bg-red-500' : score >= 70 ? 'bg-amber-500' : score >= 50 ? 'bg-yellow-500' : score >= 25 ? 'bg-blue-500' : 'bg-green-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                    />
                  </div>

                  {/* Comparative baseline */}
                  <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-xs">
                    <div>
                      <span className="text-gray-500">Linear Weighted Baseline:</span>
                      <span className="ml-1.5 font-mono font-semibold text-gray-700">{baseline.toFixed(1)}/100</span>
                    </div>
                    <div className={`flex items-center gap-0.5 font-semibold ${
                      delta > 0 ? 'text-amber-700' : delta < 0 ? 'text-blue-700' : 'text-gray-600'
                    }`}>
                      {delta > 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                      <span>{delta > 0 ? `+${delta.toFixed(1)} pts` : `${delta.toFixed(1)} pts`}</span>
                    </div>
                  </div>
                </div>

                {/* Narrative explanation */}
                {simResult?.explanation_narrative && (
                  <div className="p-3 bg-stone-50 rounded-lg border border-stone-200 text-xs text-stone-700 leading-relaxed">
                    <p className="font-semibold text-stone-900 mb-1 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-accent" />
                      Academic Explainability Rationale
                    </p>
                    <p>{simResult.explanation_narrative}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Membership Degree Matrix */}
            {simResult?.membership_activations && (
              <div>
                <p className="text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
                  Linguistic Variable Membership Degrees (μ ∈ [0.0, 1.0])
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(simResult.membership_activations).map(([varName, terms]) => (
                    <div key={varName} className="p-3 bg-white rounded-lg border border-gray-200 text-xs space-y-1.5">
                      <p className="font-bold text-gray-900 capitalize border-b pb-1 text-[11px]">{varName.replace('_', ' ')}</p>
                      {Object.entries(terms).map(([term, val]) => (
                        <div key={term} className="flex justify-between items-center text-[11px]">
                          <span className={`capitalize ${val > 0 ? 'text-accent font-semibold' : 'text-gray-400'}`}>
                            {term}
                          </span>
                          <span className={`font-mono text-[10px] ${val > 0 ? 'text-gray-900 font-bold' : 'text-gray-400'}`}>
                            μ = {val.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: RULES SPECIFICATION */}
        {activeTab === 'rules' && metadata && (
          <div className="space-y-4">
            <div className="p-3 bg-stone-50 rounded-lg border border-stone-200 text-xs text-stone-700 flex items-center justify-between">
              <div>
                <span className="font-bold text-stone-900">Inference Architecture:</span> Mamdani Min-Max · 
                <span className="font-bold text-stone-900 ml-2">Defuzzification:</span> Centroid (Center of Gravity) · 
                <span className="font-bold text-stone-900 ml-2">Total Rules:</span> {metadata.rules_count}
              </div>
              <span className="text-[11px] font-medium bg-green-100 text-green-800 px-2 py-0.5 rounded border border-green-200">
                Complete Coverage: 100%
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              {metadata.rule_base?.map((r: string, idx: number) => {
                const isCrit = r.includes('priority IS critical');
                const isHigh = r.includes('priority IS high');
                const isMedHigh = r.includes('priority IS medium_high');
                const isMed = r.includes('priority IS medium') && !isMedHigh;
                const isLow = r.includes('priority IS low');

                const borderTag = isCrit
                  ? 'border-red-200 bg-red-50/40 text-red-900'
                  : isHigh
                  ? 'border-amber-200 bg-amber-50/40 text-amber-900'
                  : isMedHigh
                  ? 'border-yellow-200 bg-yellow-50/40 text-yellow-900'
                  : isMed
                  ? 'border-blue-200 bg-blue-50/40 text-blue-900'
                  : 'border-green-200 bg-green-50/40 text-green-900';

                return (
                  <div key={idx} className={`p-2.5 rounded-md border font-mono text-[11px] leading-relaxed ${borderTag}`}>
                    {r}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 3: BENCHMARK DATASET */}
        {activeTab === 'benchmark' && benchmarkData && (
          <div className="space-y-4">
            {/* Aggregate Benchmark Summary */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-[11px] text-gray-500">Benchmark Records</p>
                <p className="text-xl font-bold text-gray-900 mt-0.5">{benchmarkData.total_records}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-[11px] text-gray-500">Avg Mamdani Priority</p>
                <p className="text-xl font-bold text-accent mt-0.5">{benchmarkData.summary.average_fuzzy_priority}/100</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-[11px] text-gray-500">Avg Linear Baseline</p>
                <p className="text-xl font-bold text-gray-700 mt-0.5">{benchmarkData.summary.average_baseline_score}/100</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-[11px] text-gray-500">Non-linear Escalations</p>
                <p className="text-xl font-bold text-amber-600 mt-0.5">{benchmarkData.summary.cases_elevated_by_fuzzy} cases</p>
              </div>
            </div>

            {/* Sample Table */}
            <div className="overflow-x-auto border border-gray-200 rounded-md">
              <table className="w-full text-xs text-left">
                <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 uppercase font-medium text-[10px]">
                  <tr>
                    <th className="py-2 px-3">Ref ID</th>
                    <th className="py-2 px-3">Distress Type</th>
                    <th className="py-2 px-3">Road & City</th>
                    <th className="py-2 px-3 text-right">Severity</th>
                    <th className="py-2 px-3 text-right">Traffic</th>
                    <th className="py-2 px-3 text-right">Waiting</th>
                    <th className="py-2 px-3 text-right">Safety</th>
                    <th className="py-2 px-3 text-right">Fuzzy Priority</th>
                    <th className="py-2 px-3 text-right">Baseline</th>
                    <th className="py-2 px-3 text-center">Delta</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {benchmarkData.records_sample.slice(0, 15).map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50/50">
                      <td className="py-2 px-3 font-mono font-medium text-gray-900">{r.public_ref}</td>
                      <td className="py-2 px-3 text-gray-700">{r.class_description}</td>
                      <td className="py-2 px-3 text-gray-600 truncate max-w-[140px]">{r.road_segment}</td>
                      <td className="py-2 px-3 text-right font-mono">{r.provisional_severity_score.toFixed(1)}</td>
                      <td className="py-2 px-3 text-right font-mono">{r.traffic_exposure_score.toFixed(1)}</td>
                      <td className="py-2 px-3 text-right font-mono">{Math.round(r.time_unresolved_days)}d</td>
                      <td className="py-2 px-3 text-right font-mono">{r.safety_urgency_score.toFixed(1)}</td>
                      <td className="py-2 px-3 text-right font-mono font-bold text-gray-900">{r.fuzzy_priority_score.toFixed(1)}</td>
                      <td className="py-2 px-3 text-right font-mono text-gray-500">{r.baseline_weighted_score.toFixed(1)}</td>
                      <td className="py-2 px-3 text-center">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold ${
                          r.decision_delta >= 5.0
                            ? 'bg-amber-100 text-amber-800'
                            : r.decision_delta <= -5.0
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {r.decision_delta > 0 ? `+${r.decision_delta.toFixed(1)}` : `${r.decision_delta.toFixed(1)}`}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-gray-500 italic">
              Showing first 15 of 250 records from `analytics/fixtures/soft_computing_maintenance_benchmark.csv`.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
