# Paventra — Production Deployment Guide & Operations Manual

This guide documents the procedures, configurations, and verification steps required to transition Paventra from local development (SQLite/Vite) to a public-facing, high-availability production deployment (PostgreSQL/PostGIS, Nginx/Caddy, persistent media storage).

---

## 1. Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │    Public Internet (Citizens & Crews)   │
                      └────────────────────┬────────────────────┘
                                           │ HTTPS (443)
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │    Reverse Proxy (Nginx / Caddy / ALB)   │
                      │  - TLS Termination                      │
                      │  - Request Size Limit (10MB image, 100MB)│
                      │  - Static Asset Caching                 │
                      └────────────┬───────────────┬────────────┘
                                   │               │
       / (Static SPA bundle)       │               │ /api/v1/* (Reverse Proxy)
                                   ▼               ▼
                      ┌─────────────────┐  ┌────────────────────────────────────┐
                      │ Static Hosting  │  │ FastAPI Application (Uvicorn)      │
                      │ (S3 / Nginx)    │  │ BEHIND_TRUSTED_PROXY=true          │
                      └─────────────────┘  │ RATE_LIMIT_REPORTS_PER_HOUR=10     │
                                           └──────────┬──────────────┬──────────┘
                                                      │              │
                                                      │              ▼
                                                      │     ┌───────────────────┐
                                                      │     │  Redis Cluster    │
                                                      │     │  (Distributed RL) │
                                                      │     └───────────────────┘
                                                      ▼
                      ┌───────────────────────────────┬─────────────────────────┐
                      │                               │                         │
                      ▼                               ▼                         ▼
          ┌───────────────────────┐       ┌───────────────────────┐ ┌───────────────────┐
          │ PostgreSQL + PostGIS  │       │ Persistent Block Vol  │ │ YOLOv8 Weights    │
          │ Relational Database   │       │ /uploads (NFS/EBS/EFS)│ │ rdd2022_yolov8n.pt│
          └───────────────────────┘       └───────────────────────┘ └───────────────────┘
```

---

## 2. Production Database Setup (PostgreSQL + PostGIS)

### 2.1 Database Provisioning
Run on your managed PostgreSQL host (PostgreSQL 15+ recommended):
```sql
CREATE DATABASE paventra;
CREATE USER paventra_app WITH ENCRYPTED PASSWORD 'replace_with_strong_password';
GRANT ALL PRIVILEGES ON DATABASE paventra TO paventra_app;

-- Connect to paventra database
\c paventra;

-- Enable PostGIS for geospatial indexing and distance operations
CREATE EXTENSION IF NOT EXISTS postgis;
GRANT ALL ON SCHEMA public TO paventra_app;
```

### 2.2 Environment Configuration
In `backend/.env` (or via Kubernetes/container environment variables):
```env
ENVIRONMENT=production
SECRET_KEY=generate_using_openssl_rand_hex_32_replace_me
DATABASE_URL=postgresql+asyncpg://paventra_app:replace_with_strong_password@postgres-host:5432/paventra
BEHIND_TRUSTED_PROXY=true
CORS_ORIGINS=["https://paventra.yourmunicipality.gov"]
UPLOAD_DIR=/mnt/paventra_storage/uploads
RATE_LIMIT_REPORTS_PER_HOUR=10
REDIS_URL=redis://:redis_password@redis-host:6379/0
MODEL_ENABLED=true
MODEL_WEIGHTS_PATH=/app/ml/weights/rdd2022_yolov8n.pt
MODEL_DEVICE=cpu
```

### 2.3 Running Database Migrations
Always run Alembic migrations during container deployment before traffic is served:
```bash
cd backend
python -m alembic upgrade head
```
Verify current revision:
```bash
python -m alembic current
# Expected: 0001_initial (head)
```

---

## 3. Persistent Media Storage Requirements

Uploaded citizen evidence, after-repair inspection photos, and survey video frames require durable, shared storage across application instances:

1. **Volume Mount:** Mount an Amazon EBS/EFS volume, Azure Files share, or NFS volume at `/mnt/paventra_storage/uploads`.
2. **Directory Permissions:**
   Ensure the application process (`paventra` user, UID 1001) has read/write permissions:
   ```bash
   chown -R 1001:1001 /mnt/paventra_storage/uploads
   chmod -R 750 /mnt/paventra_storage/uploads
   ```
3. **Subdirectories:** The application automatically creates:
   - `uploads/reports/` (original citizen report photographs)
   - `uploads/completions/` (after-repair photos uploaded by repair crews)
   - `uploads/inspections/` (video survey frames and metadata tracks)
4. **Backup Strategy:** Configure daily snapshot backups with a 30-day retention policy. Media records in the database reference relative paths under `UPLOAD_DIR`.

---

## 4. Reverse Proxy & Security Hardening (Nginx Configuration)

```nginx
# /etc/nginx/sites-available/paventra.conf
server {
    listen 80;
    server_name paventra.yourmunicipality.gov;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name paventra.yourmunicipality.gov;

    ssl_certificate /etc/letsencrypt/live/paventra.yourmunicipality.gov/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/paventra.yourmunicipality.gov/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Maximum payload size (100MB for video surveys; 10MB for photos)
    client_max_body_size 100M;

    # Frontend React Single Page App
    location / {
        root /var/www/paventra/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend FastAPI Application
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

---

## 5. Pre-Flight Production Deployment Checklist

| Verification Item | Command / Check | Required State |
| :--- | :--- | :--- |
| **Secret Key Rotation** | `openssl rand -hex 32` | Non-default secret configured in `.env`. Server will abort startup if default value is detected in `ENVIRONMENT=production`. |
| **CORS Lockdown** | Inspect `CORS_ORIGINS` in `.env` | Must match exact production domain(s) (no wildcards `*`). |
| **Trusted Proxy Mode** | `BEHIND_TRUSTED_PROXY=true` | Configured so reverse proxy headers (`X-Forwarded-For`) resolve real client IPs for rate limiting. |
| **Database Migrations** | `python -m alembic upgrade head` | Returns `0001_initial (head)`. |
| **Database Backups** | `pg_dump -U paventra_app -h ... paventra > backup.sql` | Automated cron job or cloud managed snapshot configured. |
| **Health Monitoring** | `curl -f https://paventra.yourmunicipality.gov/api/ready` | Returns `{"status":"ready","database":"connected","model_available":true}`. |
| **Model Pre-warming** | Check startup logs | `Paventra API ready (model_available=True)`. Model weights must be readable on disk. |
| **Rate Limit Protection** | Send > 10 requests from single IP | Returns `HTTP 429 Too Many Requests`. |
| **Local Dev Compatibility** | `DATABASE_URL=sqlite+aiosqlite:///./paventra.db` | SQLite remains fully operational for zero-configuration local development. |
