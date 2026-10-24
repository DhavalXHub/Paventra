"""Inspection API endpoints for Method B automated inspections."""
import shutil
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
from app.schemas.schemas import InspectionJobOut
from app.services.vision.video_inspection import process_inspection_job_async
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
    upload_dir = Path(settings.UPLOAD_DIR) / "inspections"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    media_path = upload_dir / f"src_{media_file.filename}"
    with open(media_path, "wb") as buffer:
        shutil.copyfileobj(media_file.file, buffer)

    gps_path_str = None
    if gps_track_file:
        gps_path = upload_dir / f"gps_{gps_track_file.filename}"
        with open(gps_path, "wb") as buffer:
            shutil.copyfileobj(gps_track_file.file, buffer)
        gps_path_str = str(gps_path)

    job = InspectionJob(
        submitted_by_id=current_user.id,
        status=InspectionStatus.QUEUED,
        media_type="video" if "video" in (media_file.content_type or "") else "images",
        source_path=str(media_path),
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
