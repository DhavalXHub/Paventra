"""Inspection job and frame models."""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Text, DateTime, Enum, Integer, Float, JSON, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class InspectionStatus(str, PyEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class InspectionJob(Base):
    __tablename__ = "inspection_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submitted_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[InspectionStatus] = mapped_column(
        Enum(InspectionStatus), nullable=False, default=InspectionStatus.QUEUED
    )
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_path: Mapped[str] = mapped_column(String(512), nullable=False)
    frame_sample_rate: Mapped[int] = mapped_column(Integer, default=30)
    total_frames_sampled: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detections_count: Mapped[int] = mapped_column(Integer, default=0)
    reports_created: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    has_gps_track: Mapped[bool] = mapped_column(Boolean, default=False)
    gps_track_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    submitted_by: Mapped["User"] = relationship("User", foreign_keys=[submitted_by_id])  # noqa: F821
    frames: Mapped[list["InspectionFrame"]] = relationship(
        "InspectionFrame", back_populates="job", cascade="all, delete-orphan"
    )


class InspectionFrame(Base):
    __tablename__ = "inspection_frames"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("inspection_jobs.id"), nullable=False, index=True)
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    frame_path: Mapped[str] = mapped_column(String(512), nullable=False)
    annotated_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timestamp_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    detections: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    report_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("reports.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    job: Mapped["InspectionJob"] = relationship("InspectionJob", back_populates="frames")
