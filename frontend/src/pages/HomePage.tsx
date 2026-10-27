import React from 'react';
import { Link } from 'react-router-dom';
import {
  Camera,
  MapPin,
  Search,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  Cpu,
  BarChart3,
  Layers,
  Wrench,
  Navigation,
  FileText,
  AlertTriangle,
  Flame,
  Check,
} from 'lucide-react';
import { PublicHeader } from '../components/PublicHeader';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#fafaf8] text-stone-900 flex flex-col font-sans">
      <PublicHeader current="home" />

      <main className="flex-1">
        {/* ─── 1. HERO SECTION ─── */}
        <section className="relative overflow-hidden pt-12 pb-20 md:pt-16 md:pb-28 border-b border-stone-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
              {/* Hero Left Content */}
              <div className="lg:col-span-7 space-y-6">
                {/* Civic Positioning Badge */}
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-stone-100 border border-stone-200 text-xs font-semibold text-stone-700">
                  <span className="w-2 h-2 rounded-full bg-[#14462a]" />
                  <span>Open Civic Road Intelligence Platform</span>
                </div>

                {/* Primary Headline */}
                <h1 className="text-4xl sm:text-5xl lg:text-[3.25rem] font-bold text-stone-900 tracking-tight leading-[1.12]">
                  Making road damage visible.{' '}
                  <span className="text-[#14462a]">Getting repairs moving.</span>
                </h1>

                {/* Plain Language Subtitle */}
                <p className="text-base sm:text-lg text-stone-600 max-w-2xl leading-relaxed">
                  Paventra connects citizens, Computer Vision road distress detection, and municipal
                  maintenance teams. Pin potholes with ride-hailing precision, receive transparent
                  status updates, and follow every fix from citizen upload to verified repair.
                </p>

                {/* Dual Action CTAs */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 pt-2">
                  <Link
                    to="/report"
                    className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-[#14462a] text-white text-sm font-semibold hover:bg-[#0f3620] active:scale-98 shadow-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#14462a]"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Report road damage</span>
                    <ArrowRight className="w-4 h-4 ml-0.5" />
                  </Link>

                  <Link
                    to="/track"
                    className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-white border border-stone-300 text-stone-700 text-sm font-semibold hover:bg-stone-50 hover:border-stone-400 active:scale-98 shadow-sm transition-all"
                  >
                    <Search className="w-4 h-4 text-stone-500" />
                    <span>Track a report</span>
                  </Link>
                </div>

                {/* Assurance & Governance Pill */}
                <div className="flex flex-wrap items-center gap-4 pt-4 text-xs text-stone-500">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-[#14462a]" />
                    <span>Real-time GPS pin precision</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-[#14462a]" />
                    <span>Photo-verified after-repair proof</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-[#14462a]" />
                    <span>RDD2022 AI distress detection</span>
                  </div>
                </div>
              </div>

              {/* Hero Right Visual: Authentic Product Intelligence Mockup */}
              <div className="lg:col-span-5 relative">
                <div className="relative mx-auto max-w-md lg:max-w-none bg-white rounded-2xl border border-stone-200 shadow-xl overflow-hidden">
                  {/* Mockup Header Bar */}
                  <div className="px-4 py-3 bg-stone-50 border-b border-stone-200 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                      <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                      <span className="text-xs font-mono text-stone-600 ml-1 font-semibold">
                        FIELD OBSERVATION · PAV-88C21B40
                      </span>
                    </div>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                      Under Review
                    </span>
                  </div>

                  {/* Inspection Viewport with Real Bounding Box Simulation */}
                  <div className="relative h-60 bg-stone-900 overflow-hidden flex items-center justify-center">
                    {/* Simulated Asphalt Surface Texture */}
                    <div
                      className="absolute inset-0 opacity-40 bg-[radial-gradient(#444_1px,transparent_1px)]"
                      style={{ backgroundSize: '12px 12px' }}
                    />

                    {/* Asphalt Pavement Cavity Simulation */}
                    <div className="relative w-44 h-32 rounded-full bg-stone-950/90 border border-stone-800 flex items-center justify-center shadow-inner">
                      {/* Deep Cavity Shadow */}
                      <div className="w-28 h-20 rounded-full bg-black/90 blur-[1px]" />

                      {/* Computer Vision Detected Bounding Box Overlay */}
                      <div className="absolute inset-0 border-2 border-dashed border-emerald-400 rounded-lg animate-pulse" />
                      <div className="absolute -top-3 left-2 bg-[#14462a] text-emerald-100 text-[10px] font-mono font-bold px-2 py-0.5 rounded shadow">
                        D40: POTHOLE · 88% CONF
                      </div>
                    </div>

                    {/* Secondary Linear Crack Bounding Box */}
                    <div className="absolute top-6 right-6 border border-blue-400/80 rounded px-2 py-1 bg-blue-950/40">
                      <span className="text-[9px] font-mono text-blue-300">
                        D10: TRANSVERSE CRACK · 81%
                      </span>
                    </div>

                    {/* Floating Geotag Pill */}
                    <div className="absolute bottom-3 left-3 bg-stone-900/90 backdrop-blur-sm border border-stone-700 px-2.5 py-1 rounded text-[11px] text-stone-300 flex items-center gap-1.5 font-mono">
                      <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                      <span>19.0760° N, 72.8777° E (±8m GPS)</span>
                    </div>
                  </div>

                  {/* Intelligence Assessment Breakdown */}
                  <div className="p-4 bg-white space-y-3">
                    <div className="grid grid-cols-2 gap-3 text-xs border-b border-stone-100 pb-3">
                      <div>
                        <p className="text-[11px] font-medium text-stone-500 uppercase tracking-wider">
                          Distress Classification
                        </p>
                        <p className="font-semibold text-stone-900 mt-0.5">
                          Structural Pothole (D40)
                        </p>
                      </div>
                      <div>
                        <p className="text-[11px] font-medium text-stone-500 uppercase tracking-wider">
                          2D Area Severity
                        </p>
                        <p className="font-semibold text-amber-700 mt-0.5">
                          High (11.8% road area)
                        </p>
                      </div>
                    </div>

                    {/* Mamdani Fuzzy Prioritization Score Bar */}
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-semibold text-stone-800 flex items-center gap-1">
                          <Flame className="w-3.5 h-3.5 text-orange-600" />
                          Mamdani Fuzzy Priority Score
                        </span>
                        <span className="font-mono font-bold text-stone-900">84 / 100</span>
                      </div>
                      <div className="w-full h-2 bg-stone-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-amber-500 to-red-500 rounded-full"
                          style={{ width: '84%' }}
                        />
                      </div>
                      <p className="text-[11px] text-stone-500 mt-1">
                        Driven by high traffic arterial classification &amp; safety hazard profile.
                      </p>
                    </div>

                    {/* Transparent AI Disclaimer */}
                    <div className="p-2.5 bg-stone-50 border border-stone-200 rounded-lg text-[11px] text-stone-600 flex items-start gap-2">
                      <ShieldCheck className="w-3.5 h-3.5 text-[#14462a] flex-shrink-0 mt-0.5" />
                      <span>
                        <strong>Provisional Pre-Screening:</strong> AI predictions provide municipal
                        coordinators with immediate prioritization. Final repair dispatch requires on-site human verification.
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ─── 2. HOW IT WORKS (TRUST & PROCESS) ─── */}
        <section id="how-it-works" className="py-20 bg-white border-b border-stone-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-2xl mx-auto mb-16">
              <span className="text-xs font-bold text-[#14462a] uppercase tracking-wider">
                Transparent Civic Workflow
              </span>
              <h2 className="text-3xl font-bold text-stone-900 tracking-tight mt-2">
                Three clear steps from road defect to concrete repair
              </h2>
              <p className="text-stone-600 text-sm sm:text-base mt-3">
                No bureaucratic black holes or ignored complaint tickets. Paventra provides an
                auditable pipeline from citizen reporting to crew verification.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Step 1 */}
              <div className="p-6 rounded-2xl bg-[#fafaf8] border border-stone-200 hover:border-stone-300 transition-all space-y-4">
                <div className="w-12 h-12 rounded-xl bg-[#14462a] text-white flex items-center justify-center shadow-sm">
                  <Camera className="w-6 h-6" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-[#14462a] bg-stone-200/80 px-2 py-0.5 rounded">
                    STEP 01
                  </span>
                  <h3 className="text-lg font-bold text-stone-900">Capture the defect</h3>
                </div>
                <p className="text-sm text-stone-600 leading-relaxed">
                  Take or upload a clear photo of the pavement damage. Computer Vision pre-screens
                  the distress type (pothole, transverse crack, alligator cracking) and estimates
                  surface damage area ratio.
                </p>
              </div>

              {/* Step 2 */}
              <div className="p-6 rounded-2xl bg-[#fafaf8] border border-stone-200 hover:border-stone-300 transition-all space-y-4">
                <div className="w-12 h-12 rounded-xl bg-[#14462a] text-white flex items-center justify-center shadow-sm">
                  <Navigation className="w-6 h-6" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-[#14462a] bg-stone-200/80 px-2 py-0.5 rounded">
                    STEP 02
                  </span>
                  <h3 className="text-lg font-bold text-stone-900">Pin location like a ride</h3>
                </div>
                <p className="text-sm text-stone-600 leading-relaxed">
                  Our ride-hailing style location picker captures your device GPS with meter accuracy
                  and lets you drag the map to place the fixed pin directly over the pavement fault.
                  Instant reverse-geocoding displays the exact street.
                </p>
              </div>

              {/* Step 3 */}
              <div className="p-6 rounded-2xl bg-[#fafaf8] border border-stone-200 hover:border-stone-300 transition-all space-y-4">
                <div className="w-12 h-12 rounded-xl bg-[#14462a] text-white flex items-center justify-center shadow-sm">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-[#14462a] bg-stone-200/80 px-2 py-0.5 rounded">
                    STEP 03
                  </span>
                  <h3 className="text-lg font-bold text-stone-900">Track to verified repair</h3>
                </div>
                <p className="text-sm text-stone-600 leading-relaxed">
                  Receive an immutable tracking reference (e.g. <code>PAV-XXXXXXXX</code>). Follow
                  coordinator verification, crew assignment, and inspect mandatory after-repair
                  photographic proof when the work order is marked resolved.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ─── 3. ROAD INTELLIGENCE (ACTUAL IMPLEMENTED CAPABILITIES) ─── */}
        <section id="intelligence" className="py-20 bg-[#fafaf8] border-b border-stone-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <span className="text-xs font-bold text-[#14462a] uppercase tracking-wider">
                Field-Grounded Architecture
              </span>
              <h2 className="text-3xl font-bold text-stone-900 tracking-tight mt-2">
                Engineered for genuine municipal road infrastructure
              </h2>
              <p className="text-stone-600 text-sm sm:text-base mt-3">
                Paventra combines practical Computer Vision, explainable fuzzy decision science, and
                spatio-temporal clustering to help road authorities triage backlog without black-box
                hallucinations.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Feature 1: RDD2022 YOLOv8 */}
              <div className="p-6 rounded-xl bg-white border border-stone-200 shadow-sm space-y-3">
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-[#14462a]">
                  <Cpu className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-stone-900">
                  RDD2022 YOLOv8 Detection
                </h3>
                <p className="text-xs text-stone-600 leading-relaxed">
                  Pre-trained neural network classifying 4 standard international road distress
                  taxonomies: Longitudinal Cracks (D00), Transverse Cracks (D10), Alligator Cracks
                  (D20), and Potholes (D40) with 2D geometric area estimations.
                </p>
              </div>

              {/* Feature 2: Mamdani Fuzzy Prioritization */}
              <div className="p-6 rounded-xl bg-white border border-stone-200 shadow-sm space-y-3">
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-[#14462a]">
                  <Layers className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-stone-900">
                  Mamdani Fuzzy Prioritization
                </h3>
                <p className="text-xs text-stone-600 leading-relaxed">
                  Evaluates 4 independent variables: physical distress severity, corridor traffic
                  exposure, unresolved wait duration, and safety urgency using <code>scikit-fuzzy</code>{' '}
                  centroid defuzzification with human-auditable rule weights.
                </p>
              </div>

              {/* Feature 3: Spatio-Temporal Duplicate Intelligence */}
              <div className="p-6 rounded-xl bg-white border border-stone-200 shadow-sm space-y-3">
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-[#14462a]">
                  <MapPin className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-stone-900">
                  Duplicate Candidate Detection
                </h3>
                <p className="text-xs text-stone-600 leading-relaxed">
                  Uses Haversine distance buffers and temporal matching windows to flag overlapping
                  citizen complaints and consolidate recurring survey observations into single
                  repair cases.
                </p>
              </div>

              {/* Feature 4: Automated Video Survey Ingestion */}
              <div className="p-6 rounded-xl bg-white border border-stone-200 shadow-sm space-y-3">
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-[#14462a]">
                  <Camera className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-stone-900">
                  Survey Video Inspection
                </h3>
                <p className="text-xs text-stone-600 leading-relaxed">
                  Processes municipal survey videos with configurable frame sampling, synchronized
                  GPX/NMEA telemetry linking, and consecutive-frame duplicate suppression so one
                  defect never creates 50 tickets.
                </p>
              </div>

              {/* Feature 5: Big Data Batch Analytics */}
              <div className="p-6 rounded-xl bg-white border border-stone-200 shadow-sm space-y-3">
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-[#14462a]">
                  <BarChart3 className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-stone-900">
                  Spatial Hotspot Analytics
                </h3>
                <p className="text-xs text-stone-600 leading-relaxed">
                  Aggregates city-wide road distress by 0.01° spatial grids (~1.1 km), cross-tabs
                  distress category matrices, and computes mean repair turnaround durations with
                  mathematical parity verification.
                </p>
              </div>

              {/* Feature 6: Human-in-the-Loop Safeguards */}
              <div className="p-6 rounded-xl bg-white border border-stone-200 shadow-sm space-y-3">
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center text-[#14462a]">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <h3 className="text-base font-bold text-stone-900">
                  Compulsory Field Verification
                </h3>
                <p className="text-xs text-stone-600 leading-relaxed">
                  Strict protocol: Automated AI estimates never authorize municipal budgets alone.
                  Coordinators verify severity on site, and repair teams must upload photographic
                  proof of the repaired road surface.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ─── 4. REPAIR LIFECYCLE (THE 7 STAGES) ─── */}
        <section id="lifecycle" className="py-20 bg-white border-b border-stone-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-2xl mx-auto mb-16">
              <span className="text-xs font-bold text-[#14462a] uppercase tracking-wider">
                Full Accountability Chain
              </span>
              <h2 className="text-3xl font-bold text-stone-900 tracking-tight mt-2">
                The 7-stage road repair lifecycle
              </h2>
              <p className="text-stone-600 text-sm mt-3">
                Every report follows a verifiable state machine. Skipped steps are strictly rejected
                by backend policy.
              </p>
            </div>

            {/* Step-by-Step Flow */}
            <div className="relative">
              <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-stone-200 -translate-y-1/2 z-0" />
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-4 relative z-10">
                {[
                  {
                    step: '01',
                    title: 'Submitted',
                    desc: 'Citizen or survey vehicle uploads image with GPS coordinates.',
                    badge: 'bg-stone-100 text-stone-700',
                  },
                  {
                    step: '02',
                    title: 'Under Review',
                    desc: 'Municipal coordinator triages duplicate matches & preliminary AI tags.',
                    badge: 'bg-amber-100 text-amber-800',
                  },
                  {
                    step: '03',
                    title: 'Verified',
                    desc: 'Official severity confirmed; fuzzy priority recalculated dynamically.',
                    badge: 'bg-blue-100 text-blue-800',
                  },
                  {
                    step: '04',
                    title: 'Assigned',
                    desc: 'Dispatched to specialized repair crew with target completion date.',
                    badge: 'bg-violet-100 text-violet-800',
                  },
                  {
                    step: '05',
                    title: 'In Progress',
                    desc: 'Repair team arrives on site and logs asphalt/patch commencement.',
                    badge: 'bg-cyan-100 text-cyan-800',
                  },
                  {
                    step: '06',
                    title: 'Verification',
                    desc: 'Crew uploads mandatory after-repair completion photo.',
                    badge: 'bg-orange-100 text-orange-800',
                  },
                  {
                    step: '07',
                    title: 'Resolved',
                    desc: 'Coordinator approves photo quality; audit record logged.',
                    badge: 'bg-emerald-100 text-emerald-800',
                  },
                ].map((item, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl bg-[#fafaf8] border border-stone-200 text-center flex flex-col items-center shadow-sm"
                  >
                    <span
                      className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-full mb-2 ${item.badge}`}
                    >
                      {item.step}
                    </span>
                    <h4 className="text-sm font-bold text-stone-900">{item.title}</h4>
                    <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ─── 5. FINAL CALL TO ACTION ─── */}
        <section className="py-20 bg-[#14462a] text-white">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
              Ready to report road damage in your community?
            </h2>
            <p className="text-emerald-100/90 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
              Help keep streets safe and durable. Submit a photograph with precision location in
              under 60 seconds, or check the progress of an existing public work order.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link
                to="/report"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-white text-[#14462a] text-sm font-semibold hover:bg-stone-100 shadow-md transition-all active:scale-95"
              >
                <Camera className="w-4 h-4" />
                <span>Report road damage now</span>
              </Link>
              <Link
                to="/track"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-[#0f3620] border border-emerald-800/80 text-emerald-100 text-sm font-semibold hover:bg-[#0c2a19] transition-all"
              >
                <Search className="w-4 h-4 text-emerald-300" />
                <span>Track an existing report</span>
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* ─── 6. FOOTER ─── */}
      <footer className="bg-stone-900 text-stone-400 text-xs border-t border-stone-800 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8 pb-8 border-b border-stone-800">
            {/* Brand Col */}
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-[#14462a] flex items-center justify-center text-white">
                  <MapPin className="w-4 h-4" />
                </div>
                <span className="font-bold text-white text-base tracking-tight">Paventra</span>
              </div>
              <p className="text-stone-400 text-xs max-w-md leading-relaxed">
                Open civic road distress intelligence and repair tracking platform. Dedicated to
                transparent road maintenance, automated distress assessment, and verifiable municipal
                work orders.
              </p>
              <p className="text-stone-500 text-[11px]">
                Independent civic technology platform. Not operated by or officially affiliated with
                any governmental department.
              </p>
            </div>

            {/* Quick Links */}
            <div>
              <p className="text-white font-semibold text-xs uppercase tracking-wider mb-3">
                Citizen Access
              </p>
              <ul className="space-y-2">
                <li>
                  <Link to="/report" className="hover:text-white transition-colors">
                    Report road damage
                  </Link>
                </li>
                <li>
                  <Link to="/track" className="hover:text-white transition-colors">
                    Track repair status
                  </Link>
                </li>
                <li>
                  <Link to="/login" className="hover:text-white transition-colors">
                    Citizen sign in
                  </Link>
                </li>
                <li>
                  <Link to="/register" className="hover:text-white transition-colors">
                    Register citizen account
                  </Link>
                </li>
              </ul>
            </div>

            {/* Operations Links */}
            <div>
              <p className="text-white font-semibold text-xs uppercase tracking-wider mb-3">
                Municipal Operations
              </p>
              <ul className="space-y-2">
                <li>
                  <Link to="/coordinator" className="hover:text-white transition-colors">
                    Coordinator Portal
                  </Link>
                </li>
                <li>
                  <Link to="/coordinator/map" className="hover:text-white transition-colors">
                    Distress Map View
                  </Link>
                </li>
                <li>
                  <Link to="/coordinator/inspections" className="hover:text-white transition-colors">
                    Video Survey Inspections
                  </Link>
                </li>
                <li>
                  <Link to="/team/jobs" className="hover:text-white transition-colors">
                    Repair Crew Portal
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-stone-500 text-[11px]">
            <p>© {new Date().getFullYear()} Paventra Civic Infrastructure. All rights reserved.</p>
            <div className="flex items-center gap-2 font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
              <span>FastAPI · React 19 · YOLOv8 · scikit-fuzzy · Leaflet</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
