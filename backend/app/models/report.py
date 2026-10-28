"""Core road report model and related sub-models."""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    String, Text, Float, DateTime, Enum, ForeignKey,
    Integer, Boolean, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ReportStatus(str, PyEnum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PENDING_VERIFICATION = "pending_verification"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class ReportSource(str, PyEnum):
    CITIZEN = "citizen"
    INSPECTION = "inspection"


class LocationSource(str, PyEnum):
    GPS = "gps"
    MANUAL = "manual"
    VIDEO_SYNC = "video_sync"
    METADATA = "metadata"
    UNKNOWN = "unknown"


class DamageType(str, PyEnum):
    POTHOLE = "pothole"
    CRACK = "crack"
    SURFACE_DETERIORATION = "surface_deterioration"
    RUTTING = "rutting"
    EDGE_BREAK = "edge_break"
    OTHER = "other"
    UNKNOWN = "unknown"


class SeverityLevel(str, PyEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    public_ref: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    source: Mapped[ReportSource] = mapped_column(Enum(ReportSource), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), nullable=False, default=ReportStatus.SUBMITTED, index=True
    )

    submitter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    submitter_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    claim_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    damage_type: Mapped[DamageType] = mapped_column(Enum(DamageType), nullable=False, default=DamageType.UNKNOWN)
    severity: Mapped[SeverityLevel | None] = mapped_column(Enum(SeverityLevel), nullable=True)
    severity_is_estimated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_source: Mapped[LocationSource] = mapped_column(
        Enum(LocationSource), nullable=False, default=LocationSource.UNKNOWN
    )
    location_accuracy_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    address_hint: Mapped[str | None] = mapped_column(String(512), nullable=True)

    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_damage_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_bounding_boxes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_inference_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority_explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    assessment_status: Mapped[str | None] = mapped_column(String(50), nullable=True, default="PENDING")
    ai_model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_assessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    original_severity: Mapped[SeverityLevel | None] = mapped_column(Enum(SeverityLevel), nullable=True)
    original_priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    override_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    inspection_frame_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submitter: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="reports", foreign_keys=[submitter_id]
    )
    reviewed_by: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by_id])  # noqa: F821
    media_assets: Mapped[list["MediaAsset"]] = relationship(
        "MediaAsset", back_populates="report", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["ReportStatusHistory"]] = relationship(
        "ReportStatusHistory", back_populates="report", cascade="all, delete-orphan"
    )
    assignment: Mapped["RepairAssignment | None"] = relationship(
        "RepairAssignment", back_populates="report", uselist=False
    )
    priority_assessment: Mapped["FuzzyPriorityAssessment | None"] = relationship(
        "FuzzyPriorityAssessment", back_populates="report", uselist=False
    )
    notifications: Mapped[list["Notification"]] = relationship(  # noqa: F821
        "Notification", back_populates="report"
    )
    duplicate_links_primary: Mapped[list["DuplicateLink"]] = relationship(
        "DuplicateLink", foreign_keys="DuplicateLink.primary_report_id", back_populates="primary_report"
    )
    duplicate_links_duplicate: Mapped[list["DuplicateLink"]] = relationship(
        "DuplicateLink", foreign_keys="DuplicateLink.duplicate_report_id", back_populates="duplicate_report"
    )

    def __repr__(self) -> str:
        return f"<Report {self.public_ref} status={self.status}>"


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, default="report_photo")
    annotated_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    report: Mapped["Report"] = relationship("Report", back_populates="media_assets")


class ReportStatusHistory(Base):
    __tablename__ = "report_status_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    changed_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    report: Mapped["Report"] = relationship("Report", back_populates="status_history")
    changed_by: Mapped["User | None"] = relationship("User", foreign_keys=[changed_by_id])  # noqa: F821


class RepairAssignment(Base):
    __tablename__ = "repair_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False, unique=True)
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("repair_teams.id"), nullable=False)
    assigned_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_photo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    report: Mapped["Report"] = relationship("Report", back_populates="assignment")
    team: Mapped["RepairTeam"] = relationship("RepairTeam", back_populates="assignments")  # noqa: F821
    assigned_by: Mapped["User"] = relationship("User", foreign_keys=[assigned_by_id])  # noqa: F821


class FuzzyPriorityAssessment(Base):
    __tablename__ = "fuzzy_priority_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False, unique=True)
    severity_input: Mapped[float] = mapped_column(Float, nullable=False)
    traffic_exposure_input: Mapped[float] = mapped_column(Float, nullable=False)
    time_unresolved_days: Mapped[float] = mapped_column(Float, nullable=False)
    safety_urgency_input: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_label: Mapped[str] = mapped_column(String(50), nullable=False)
    top_contributing_factors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    baseline_score: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    report: Mapped["Report"] = relationship("Report", back_populates="priority_assessment")


class DuplicateLink(Base):
    __tablename__ = "duplicate_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    primary_report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id"), nullable=False, index=True
    )
    duplicate_report_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reports.id"), nullable=False, index=True
    )
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    primary_report: Mapped["Report"] = relationship(
        "Report", foreign_keys=[primary_report_id], back_populates="duplicate_links_primary"
    )
    duplicate_report: Mapped["Report"] = relationship(
        "Report", foreign_keys=[duplicate_report_id], back_populates="duplicate_links_duplicate"
    )
