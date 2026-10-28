"""
Storage abstraction supporting Local Disk and Persistent Cloud Object Storage (Supabase Storage).
Preserves local development workflows while ensuring uploaded files survive ephemeral container restarts.
"""
import logging
from pathlib import Path
from typing import Optional, Tuple
import aiofiles
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND.lower()
        self.supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
        self.supabase_key = settings.SUPABASE_KEY
        self.bucket_name = settings.SUPABASE_BUCKET_NAME

    def is_cloud_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    async def save_file(
        self,
        content: bytes,
        safe_filename: str,
        folder: str = "reports",
        content_type: str = "image/jpeg",
    ) -> Tuple[str, str]:
        """
        Saves file to local disk (always, for CV inference accessibility)
        and uploads to Supabase Object Storage if configured.
        Returns: (accessible_path_or_url, safe_filename)
        """
        # Always write locally so OpenCV/YOLO can read it directly from disk
        local_dir = Path(settings.UPLOAD_DIR) / folder
        local_dir.mkdir(parents=True, exist_ok=True)
        local_file_path = local_dir / safe_filename
        async with aiofiles.open(local_file_path, "wb") as f:
            await f.write(content)

        # If Supabase cloud storage is enabled, persist to bucket
        if self.is_cloud_enabled():
            try:
                cloud_url = await self._upload_to_supabase(
                    content=content,
                    safe_filename=safe_filename,
                    folder=folder,
                    content_type=content_type,
                )
                if cloud_url:
                    return cloud_url, safe_filename
            except Exception as e:
                logger.error("Failed to upload to Supabase Storage: %s. Falling back to local storage.", e)

        # Fallback to local file path
        return str(local_file_path), safe_filename

    async def _upload_to_supabase(
        self,
        content: bytes,
        safe_filename: str,
        folder: str,
        content_type: str,
    ) -> Optional[str]:
        target_path = f"{folder}/{safe_filename}"
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{target_path}"
        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apiKey": self.supabase_key,
            "Content-Type": content_type,
            "x-upsert": "true",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, content=content, headers=headers)
            if resp.status_code in (200, 201):
                public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{target_path}"
                logger.info("Successfully persisted image to Supabase Storage: %s", public_url)
                return public_url
            else:
                logger.warning("Supabase storage upload returned status %d: %s", resp.status_code, resp.text)
                return None

    def get_public_url(self, filename: str, folder: str = "reports") -> str:
        """Returns public URL for an asset."""
        if self.is_cloud_enabled():
            return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{folder}/{filename}"
        return f"/uploads/{folder}/{filename}"


storage_service = StorageService()
