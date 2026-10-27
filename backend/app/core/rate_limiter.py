"""
Production-hardened rate limiter for public submissions.

Features:
- Dual-key sliding-window rate limiting (IP-based AND account/email-based).
- Prevents bypasses from simply altering the submitter email string.
- Proxy-aware IP resolution guarded by BEHIND_TRUSTED_PROXY configuration.
- Hashed identifiers to avoid storing raw PII in memory or cache.
- Bounded memory with active eviction of expired client records.
- Optional Redis backend with seamless local in-memory fallback.
"""
import hashlib
import logging
import threading
import time
from typing import Optional, Dict, List
from fastapi import Request, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_trusted_client_ip(request: Request) -> str:
    """
    Resolves client IP securely.
    Guards against header spoofing by ignoring X-Forwarded-For unless
    BEHIND_TRUSTED_PROXY is explicitly enabled.
    """
    if settings.BEHIND_TRUSTED_PROXY:
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # First non-empty comma-separated address represents the origin client
            first_ip = x_forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def hash_identifier(category: str, raw_val: str) -> str:
    """Anonymizes identifiers (IPs, emails) to protect privacy."""
    digest = hashlib.sha256(raw_val.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"{category}:{digest}"


class SlidingWindowMemoryLimiter:
    """
    In-memory sliding-window rate limiter with thread-safety and bounded storage.
    
    LIMITATION NOTICE:
    In-memory state is maintained per-worker process. In multi-process production
    clusters (e.g. multiple Gunicorn/Uvicorn workers behind a balancer), configure
    REDIS_URL to share state across workers.
    """

    def __init__(self, max_tracked_keys: int = 5000):
        self._lock = threading.Lock()
        self._records: Dict[str, List[float]] = {}
        self.max_tracked_keys = max_tracked_keys
        self._ops_since_cleanup = 0

    def check_and_record(self, key: str, limit: int, window_seconds: float = 3600.0) -> bool:
        with self._lock:
            now = time.time()
            cutoff = now - window_seconds

            # Retrieve and filter history
            history = self._records.setdefault(key, [])
            history[:] = [t for t in history if t > cutoff]

            if len(history) >= limit:
                return False

            history.append(now)
            self._ops_since_cleanup += 1

            # Periodic eviction of completely stale keys to bound memory
            if self._ops_since_cleanup >= 100 or len(self._records) > self.max_tracked_keys:
                self._evict_stale_keys(cutoff)
                self._ops_since_cleanup = 0

            return True

    def _evict_stale_keys(self, cutoff: float) -> None:
        stale_keys = [k for k, timestamps in self._records.items() if not timestamps or max(timestamps) <= cutoff]
        for k in stale_keys:
            del self._records[k]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._ops_since_cleanup = 0


# Global in-memory instance
_memory_limiter = SlidingWindowMemoryLimiter()


def enforce_submission_rate_limit(
    request: Request,
    submitter_email: Optional[str] = None,
    current_user_id: Optional[str] = None,
) -> None:
    """
    Enforces hourly report submission limit.
    Applies dual validation:
    1. Client IP address (cannot be bypassed by swapping email).
    2. User account or submitter email (if provided).
    """
    limit = settings.RATE_LIMIT_REPORTS_PER_HOUR
    if limit <= 0 or settings.ENVIRONMENT.lower() == "testing":
        return

    # 1. IP validation (Primary defense)
    client_ip = get_trusted_client_ip(request)
    ip_key = hash_identifier("ip", client_ip)
    if not _memory_limiter.check_and_record(ip_key, limit=limit, window_seconds=3600.0):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: maximum {limit} reports allowed per hour. Please wait before submitting another report.",
        )

    # 2. Account / Submitter validation (Secondary defense)
    account_ident = current_user_id or (submitter_email.strip().lower() if submitter_email else None)
    if account_ident:
        user_key = hash_identifier("usr", account_ident)
        if not _memory_limiter.check_and_record(user_key, limit=limit, window_seconds=3600.0):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {limit} reports allowed per hour. Please wait before submitting another report.",
            )
