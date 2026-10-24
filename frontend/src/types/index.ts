// API types matching backend schemas

export type UserRole = 'citizen' | 'coordinator' | 'repair_team' | 'admin';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: UserRole;
}

export type ReportStatus =
  | 'submitted'
  | 'under_review'
  | 'verified'
  | 'assigned'
  | 'in_progress'
  | 'pending_verification'
  | 'resolved'
  | 'rejected';

export type DamageType =
  | 'pothole'
  | 'crack'
  | 'surface_deterioration'
  | 'rutting'
  | 'edge_break'
  | 'other'
  | 'unknown';

export type SeverityLevel = 'low' | 'moderate' | 'high' | 'critical';
export type LocationSource = 'gps' | 'manual' | 'video_sync' | 'metadata' | 'unknown';
export type ReportSource = 'citizen' | 'inspection';

export interface MediaAsset {
  id: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  asset_type: string;
  uploaded_at: string;
}

export interface StatusHistory {
  from_status: string | null;
  to_status: string;
  changed_by_email: string | null;
  reason: string | null;
  notes: string | null;
  changed_at: string;
}

export interface Assignment {
  id: string;
  team_id: string;
  team_name: string | null;
  target_date: string | null;
  notes: string | null;
  completion_notes: string | null;
  assigned_at: string;
}

export interface PriorityAssessment {
  priority_score: number;
  priority_label: string;
  top_contributing_factors: Array<{ factor: string; weight: string; value: number }>;
  baseline_score: number;
  computed_at: string;
}

export interface Report {
  id: string;
  public_ref: string;
  source: ReportSource;
  status: ReportStatus;
  description: string | null;
  damage_type: DamageType;
  severity: SeverityLevel | null;
  severity_is_estimated: boolean;
  latitude: number | null;
  longitude: number | null;
  location_source: LocationSource;
  location_accuracy_meters: number | null;
  address_hint: string | null;
  ai_confidence: number | null;
  ai_damage_type: string | null;
  priority_score: number | null;
  review_reason: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  media_assets: MediaAsset[];
  status_history: StatusHistory[];
  assignment: Assignment | null;
  priority_assessment: PriorityAssessment | null;
}

export interface ReportListItem {
  id: string;
  public_ref: string;
  source: ReportSource;
  status: ReportStatus;
  damage_type: DamageType;
  severity: SeverityLevel | null;
  latitude: number | null;
  longitude: number | null;
  address_hint: string | null;
  priority_score: number | null;
  ai_confidence: number | null;
  created_at: string;
  updated_at: string;
}

export interface ReportListResponse {
  items: ReportListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Team {
  id: string;
  name: string;
  description: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Notification {
  id: string;
  title: string;
  body: string;
  notification_type: string;
  is_read: boolean;
  report_id: string | null;
  created_at: string;
  read_at: string | null;
}

export interface AnalyticsSummary {
  total_reports: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  by_severity: Record<string, number>;
  recent_7_days: number;
  overdue_count: number;
  high_severity_unverified: number;
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface SubmitConfirmation {
  public_ref: string;
  report_id: string;
  status: string;
  ai_assessment: Record<string, unknown> | null;
  message: string;
}

export interface MapMarker {
  id: string;
  public_ref: string;
  status: string;
  severity: string | null;
  damage_type: string;
  lat: number;
  lon: number;
  priority_score: number | null;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  action: string;
  actor_email: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface TrackResponse {
  public_ref: string;
  status: string;
  damage_type: string;
  severity: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  review_reason: string | null;
  history: Array<{ status: string; changed_at: string; notes: string | null }>;
}

export interface InspectionJob {
  id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'partial';
  media_type: string;
  frame_sample_rate: number;
  total_frames_sampled: number | null;
  progress_percent: number;
  detections_count: number;
  reports_created: number;
  has_gps_track: boolean;
  notes: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface InspectionFrame {
  id: string;
  job_id: string;
  frame_index: number;
  frame_path: string;
  annotated_path: string | null;
  timestamp_seconds: number | null;
  latitude: number | null;
  longitude: number | null;
  detections: Array<{
    class_code: string;
    damage_type: string;
    confidence: number;
    bbox: number[];
  }>;
  confidence: number | null;
  is_duplicate: boolean;
  report_id: string | null;
  created_at: string;
}
