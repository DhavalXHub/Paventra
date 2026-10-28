# Paventra — Zero-Cost (₹0) Production Deployment Guide

This guide details the exact step-by-step instructions to deploy the **Paventra Road Damage Intelligence Platform** to the internet on free-tier infrastructure (₹0 cost, no credit card required).

---

## 1. Architecture Overview

- **Frontend:** **Vercel** (Free Hobby Tier) → Fast CDN, automatic HTTPS (`https://paventra.vercel.app`), zero cold starts.
- **Backend:** **Render** (Free Web Service) → FastAPI + YOLOv8n + Mamdani FIS (`https://paventra-api.onrender.com`).
- **Database:** **Supabase** (Free Tier PostgreSQL) → 500 MB persistent storage, never auto-deleted.
- **Media Storage:** **Supabase Storage** (1 GB Free Bucket) → Persistent cloud storage for citizen photos & repair completions.

---

## 2. Step 1: Provision Persistent Database & Storage (Supabase — ~3 mins)

1. Open [https://supabase.com](https://supabase.com) and click **Start your project** (Sign in with your GitHub account).
2. Click **New Project**:
   - **Name:** `paventra-db`
   - **Database Password:** Enter a strong password (e.g. `PaventraProd2026!`) and note it down.
   - **Region:** Select the closest region (e.g., `South Asia (Mumbai)` or `East US`).
   - **Pricing Plan:** Free ($0/month).
   - Click **Create new project**.
3. Retrieve your **PostgreSQL Connection String**:
   - Go to **Project Settings** (gear icon on bottom left) → **Database**.
   - Under **Connection string**, select the **URI** tab, choose **Mode: Session** (port 5432) or **Transaction** (port 6543 pooler).
   - Copy the string. It will look like:
     `postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
   - Change the prefix from `postgresql://` to `postgresql+asyncpg://` for SQLAlchemy async:
     `postgresql+asyncpg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres`
4. Create the **Storage Bucket** for uploaded photos:
   - In the left sidebar, click **Storage**.
   - Click **New Bucket**.
   - Name: `paventra-uploads`.
   - Toggle **Public bucket** to **ON** (allows browsers to view road damage photos).
   - Click **Save**.
5. Retrieve your **Supabase API Credentials**:
   - Go to **Project Settings** → **API**.
   - Copy **Project URL** (e.g. `https://xyzcompany.supabase.co`).
   - Copy the **`anon` `public`** API key.

---

## 3. Step 2: Migrate Local Data to Supabase PostgreSQL (~1 min)

Run the included migration script from your terminal to transfer all genuine users, teams, and reports from `paventra.db` to Supabase:

```powershell
cd D:\Paventra
python backend/scripts/migrate_to_postgres.py "postgresql+asyncpg://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres"
```

*This automatically builds all tables with schema constraints and copies genuine reports and user accounts. It strictly ignores test fixture artifacts.*

---

## 4. Step 3: Deploy FastAPI Backend (Render — ~4 mins)

1. Push your code to your GitHub repository:
   ```powershell
   git add .
   git commit -m "feat: configure cloud production deployment"
   git push origin main
   ```
2. Open [https://render.com](https://render.com) and sign in with GitHub.
3. Click **New +** → **Web Service**.
4. Select **Build and deploy from a Git repository** and connect your `Paventra` repository.
5. Configure the service settings:
   - **Name:** `paventra-api`
   - **Language:** `Python 3`
   - **Root Directory:** `backend`
   - **Region:** Choose the region closest to your Supabase database (e.g., `Oregon` or `Frankfurt`).
   - **Branch:** `main`
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu && pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan:** **Free** ($0/month).
6. Click **Advanced** and add these **Environment Variables**:

| Variable | Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Enables production security safeguards |
| `PYTHON_VERSION` | `3.12.9` | Matches tested runtime |
| `SECRET_KEY` | *(Click "Generate" or type a 32+ char string)* | JWT signing key |
| `DATABASE_URL` | `postgresql+asyncpg://postgres...` | Your Supabase connection string from Step 1 |
| `CORS_ORIGINS` | `https://paventra.vercel.app,http://localhost:5173` | Allowed frontend origins |
| `MODEL_ENABLED` | `true` | Enables YOLOv8 road-damage detection |
| `MODEL_CONFIDENCE_THRESHOLD` | `0.35` | Standard RDD detection threshold |
| `STORAGE_BACKEND` | `supabase` | Directs file uploads to Supabase Storage |
| `SUPABASE_URL` | `https://[PROJECT-REF].supabase.co` | Your Supabase Project URL |
| `SUPABASE_KEY` | `[YOUR-SUPABASE-ANON-KEY]` | Your Supabase API Key |
| `SUPABASE_BUCKET_NAME` | `paventra-uploads` | Your bucket name |

7. Click **Create Web Service**.
   - Render will build the image, install CPU PyTorch, download the RDD2022 weights from Hugging Face, and start Uvicorn.
   - Once complete, copy your public backend URL: `https://paventra-api.onrender.com`.
   - Verify health check in your browser: `https://paventra-api.onrender.com/api/health`.

---

## 5. Step 4: Deploy React Frontend (Vercel — ~2 mins)

1. Open [https://vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **Add New...** → **Project**.
3. Import your `Paventra` repository.
4. Configure the project:
   - **Framework Preset:** Vite
   - **Root Directory:** Click `Edit` and select `frontend`.
   - **Build Command:** `npm run build` (Default)
   - **Output Directory:** `dist` (Default)
5. Expand **Environment Variables** and add:
   - **Name:** `VITE_API_URL`
   - **Value:** `https://paventra-api.onrender.com` *(your Render backend URL from Step 3, without trailing slash)*
6. Click **Deploy**.
   - Vercel will build the frontend in ~30 seconds and provide your live URL (e.g., `https://paventra.vercel.app`).

---

## 6. Verification Checklist for Faculty Demo

1. **Open Frontend:** Open your Vercel URL on any computer or phone.
2. **Cold Start Note:** Because Render's free tier sleeps after 15 minutes of inactivity, allow ~40 seconds on the very first API request after an idle period for the container to wake up.
3. **Login as Coordinator:**
   - **Email:** `coordinator@paventra.local`
   - **Password:** `Paventra2024!`
   - Open `/coordinator/reports`: Verify genuine reports appear in the **Recent Citizen Submissions** showcase and **Actionable Priority Queue**.
4. **Submit a New Citizen Report:**
   - Go to Public Report page, select location on map or enter coordinates, upload a road damage photo, and submit.
   - Observe automatic YOLO inference and Mamdani priority calculation.
   - Open `/coordinator/reports`: Verify the new report appears instantly at the top of Recent Citizen Submissions.
   - Verify the uploaded photo loads properly from the Supabase bucket.
