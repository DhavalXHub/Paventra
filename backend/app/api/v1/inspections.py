"""Inspection API endpoints for Method B automated inspections."""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import get_db, require_coordinator
from app.models.user import User
from app.models.inspection import InspectionJob, InspectionFrame, InspectionStatus
from app.models.report import Report
from app.schemas.schemas import InspectionJobOut, InspectionFrameOut
from app.services.vision.video_inspection import (
    process_inspection_job_async,
    resolve_inspection_file_path,
    validate_video_file,
)
from app.services.media.validation import safe_upload_name
from app.db.database import AsyncSessionLocal

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.get("", response_model=List[InspectionJobOut])
async def list_inspections(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(select(InspectionJob).order_by(InspectionJob.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=InspectionJobOut, status_code=201)
async def create_inspection_job(
    background_tasks: BackgroundTasks,
    media_file: UploadFile = File(...),
    gps_track_file: Optional[UploadFile] = File(None),
    sample_rate: int = Form(30),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_coordinator),
):
    inspections_dir = settings.upload_path / "inspections"
    inspections_dir.mkdir(parents=True, exist_ok=True)

    media_bytes = await media_file.read()
    if not media_bytes or len(media_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded video file is empty")

    if len(media_bytes) > settings.max_video_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Video exceeds {settings.MAX_VIDEO_UPLOAD_SIZE_MB} MB limit",
        )
    media_name = safe_upload_name(media_file.filename, default_ext=".mp4")
    abs_media_path = inspections_dir / media_name
    abs_media_path.write_bytes(media_bytes)
    db_media_path = str(Path("uploads") / "inspections" / media_name)

    gps_path_str = None
    if gps_track_file:
        gps_bytes = await gps_track_file.read()
        if len(gps_bytes) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="GPS track file is too large")
        gps_name = safe_upload_name(gps_track_file.filename, default_ext=".json")
        abs_gps_path = inspections_dir / gps_name
        abs_gps_path.write_bytes(gps_bytes)
        gps_path_str = str(Path("uploads") / "inspections" / gps_name)

    job = InspectionJob(
        submitted_by_id=current_user.id,
        status=InspectionStatus.QUEUED,
        media_type="video" if "video" in (media_file.content_type or "") else "images",
        source_path=db_media_path,
        frame_sample_rate=max(1, sample_rate),
        has_gps_track=gps_path_str is not None,
        gps_track_path=gps_path_str,
        notes=notes,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue background task
    background_tasks.add_task(process_inspection_job_async, job.id, AsyncSessionLocal)

    return job


@router.post("/{job_id}/retry", response_model=InspectionJobOut)
async def retry_inspection_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(select(InspectionJob).where(InspectionJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Inspection job not found")

    if job.status == InspectionStatus.PROCESSING:
        raise HTTPException(status_code=409, detail="Inspection job is currently processing")

    # Validate source video file exists and has valid size
    resolved_path = resolve_inspection_file_path(job.source_path)
    is_valid, error_msg = validate_video_file(resolved_path)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry job: {error_msg}. Please upload a new video.",
        )

    # Avoid duplicate reports and frames: delete any existing frames and reports for this job
    frame_res = await db.execute(select(InspectionFrame).where(InspectionFrame.job_id == job.id))
    existing_frames = frame_res.scalars().all()
    frame_ids = [f.id for f in existing_frames]

    if frame_ids:
        report_res = await db.execute(select(Report).where(Report.inspection_frame_id.in_(frame_ids)))
        linked_reports = report_res.scalars().all()
        for rpt in linked_reports:
            await db.delete(rpt)
        for f in existing_frames:
            await db.delete(f)
        await db.flush()

    # Reset job counters and state
    job.status = InspectionStatus.QUEUED
    job.progress_percent = 0.0
    job.error_message = None
    job.detections_count = 0
    job.reports_created = 0
    job.total_frames_sampled = None
    job.started_at = None
    job.completed_at = None
    await db.commit()
    await db.refresh(job)

    # Re-queue background processing
    background_tasks.add_task(process_inspection_job_async, job.id, AsyncSessionLocal)

    return job


@router.get("/{job_id}", response_model=InspectionJobOut)
async def get_inspection_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(select(InspectionJob).where(InspectionJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Inspection job not found")
    return job


@router.get("/{job_id}/frames", response_model=List[InspectionFrameOut])
async def list_inspection_frames(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_coordinator),
):
    result = await db.execute(
        select(InspectionFrame)
        .where(InspectionFrame.job_id == job_id)
        .order_by(InspectionFrame.frame_index.asc())
    )
    return list(result.scalars().all())
