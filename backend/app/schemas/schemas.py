"""Pydantic schemas for all domain objects."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=8)
    role: str = "citizen"


# ─── Reports ─────────────────────────────────────────────────────────────────

class ReportSubmit(BaseModel):
    description: Optional[str] = Field(None, max_length=2000)
    damage_type: str = "unknown"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: str = "unknown"
    location_accuracy_meters: Optional[float] = None
    address_hint: Optional[str] = Field(None, max_length=512)
    submitter_email: Optional[str] = None

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v


class MediaAssetOut(BaseModel):
    id: str
    file_name: str
    mime_type: str
    file_size_bytes: int
    asset_type: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class StatusHistoryOut(BaseModel):
    from_status: Optional[str]
    to_status: str
    changed_by_email: Optional[str]
    reason: Optional[str]
    notes: Optional[str]
    changed_at: datetime

    model_config = {"from_attributes": True}


class AssignmentOut(BaseModel):
    id: str
    team_id: str
    team_name: Optional[str] = None
    target_date: Optional[datetime]
    notes: Optional[str]
    completion_notes: Optional[str]
    assigned_at: datetime

    model_config = {"from_attributes": True}


class PriorityAssessmentOut(BaseModel):
    priority_score: float
    priority_label: str
    top_contributing_factors: list[dict]
    baseline_score: float
    computed_at: datetime

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: str
    public_ref: str
    source: str
    status: str
    description: Optional[str]
    damage_type: str
    severity: Optional[str]
    severity_is_estimated: bool
    latitude: Optional[float]
    longitude: Optional[float]
    location_source: str
    location_accuracy_meters: Optional[float]
    address_hint: Optional[str]
    ai_confidence: Optional[float]
    ai_damage_type: Optional[str]
    priority_score: Optional[float]
    review_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    media_assets: list[MediaAssetOut] = []
    status_history: list[StatusHistoryOut] = []
    assignment: Optional[AssignmentOut] = None
    priority_assessment: Optional[PriorityAssessmentOut] = None

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    id: str
    public_ref: str
    source: str
    status: str
    damage_type: str
    severity: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    address_hint: Optional[str]
    priority_score: Optional[float]
    ai_confidence: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportListItem]
    total: int
    page: int
    page_size: int
    pages: int


class StatusUpdateRequest(BaseModel):
    status: str
    reason: Optional[str] = None
    notes: Optional[str] = None


class AssignRequest(BaseModel):
    team_id: str
    target_date: Optional[datetime] = None
    notes: Optional[str] = None


class CompletionRequest(BaseModel):
    completion_notes: str
    target_date: Optional[datetime] = None


# ─── Teams ───────────────────────────────────────────────────────────────────

class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class TeamOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Notifications ────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: str
    title: str
    body: str
    notification_type: str
    is_read: bool
    report_id: Optional[str]
    created_at: datetime
    read_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ─── Analytics ───────────────────────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_reports: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    by_severity: dict[str, int]
    recent_7_days: int
    overdue_count: int
    high_severity_unverified: int


class TrendPoint(BaseModel):
    date: str
    count: int


# ─── Inspections ─────────────────────────────────────────────────────────────

class InspectionFrameOut(BaseModel):
    id: str
    job_id: str
    frame_index: int
    frame_path: str
    annotated_path: Optional[str]
    timestamp_seconds: Optional[float]
    latitude: Optional[float]
    longitude: Optional[float]
    detections: list[dict]
    confidence: Optional[float]
    is_duplicate: bool
    report_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionJobOut(BaseModel):
    id: str
    status: str
    media_type: str
    frame_sample_rate: int
    total_frames_sampled: Optional[int]
    progress_percent: float
    detections_count: int
    reports_created: int
    has_gps_track: bool
    notes: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ─── Submission confirmation ──────────────────────────────────────────────────

class SubmitConfirmation(BaseModel):
    public_ref: str
    report_id: str
    status: str
    ai_assessment: Optional[dict[str, Any]] = None
    message: str
