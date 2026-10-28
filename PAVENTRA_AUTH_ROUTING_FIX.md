# PAVENTRA — AUTHENTICATION, ROLE-BASED REDIRECTION, AND SESSION ISOLATION FIX REPORT

**Project:** Paventra — AI-Powered Road Damage Intelligence and Repair Management  
**Workspace:** `D:\Paventra`  
**Date:** October 29, 2026  
**Status:** **RESOLVED & VERIFIED**

---

## 1. Executive Summary & Root Cause Analysis

### The Bug Observed
1. A citizen signs in (e.g. via Google authentication).
2. The citizen submits a road-damage report or accesses `/my-reports`.
3. The citizen signs out.
4. The coordinator signs in (`coordinator@paventra.local`).
5. Instead of directly landing on the Coordinator Dashboard (`/coordinator`), the application displayed the citizen-facing interface (`/my-reports` or `/report`).
6. Clicking Home or navigating would land on the public homepage with `PublicHeader`.
7. The coordinator had to manually click the "Coordinator" account link in `PublicHeader` to reach `/coordinator`.

### The Exact Root Cause Identified

1. **Stale / Incompatible `fromPath` Hijacking in `LoginPage.tsx`:**
   - In `LoginPage.tsx`, the redirect logic read:
     ```tsx
     const fromPath = (location.state as { from?: { pathname?: string } })?.from?.pathname;
     ...
     if (fromPath && fromPath !== '/login' && fromPath !== '/register') {
       navigate(fromPath);
       return;
     }
     ```
   - When a citizen was at `/my-reports` and signed out, `RequireAuth` in `App.tsx` caught the unauthenticated state during the transition and routed to `/login` with `state: { from: { pathname: '/my-reports' } }`.
   - When the coordinator subsequently signed in, `LoginPage.tsx` blindly honored `fromPath` (`'/my-reports'`), bypassing role landing logic and navigating the coordinator into the citizen portal!
   - On `/my-reports`, clicking "Home" routed to `/` (the public homepage). In `PublicHeader.tsx`, the authenticated user was recognized as a coordinator with an account button linking to `/coordinator`. Only clicking that link rescued the coordinator.

2. **Absence of Role-Permission Verification on `fromPath`:**
   - The login redirect had no permission check to verify whether `fromPath` was authorized for the newly logged-in role.
   - Coordinators were sent to citizen pages (`/my-reports`, `/report`), while citizens could be directed to `/coordinator` and bounced.

3. **Missing `isInitializing` State in `AuthContext.tsx` & Premature Route Guard Redirection:**
   - `AuthContext` had no `isInitializing` state to track whether token validation via `/auth/me` was in progress.
   - On page refresh or slow network, `RequireCoordinator` in `App.tsx` saw `!isCoordinator` before `/auth/me` responded and executed `return <Navigate to="/report" replace />;`, bouncing coordinators into the citizen damage reporting page.

4. **Incomplete Session Data Isolation on Logout:**
   - `logout()` removed tokens from `localStorage` and reset React state, but **did not purge TanStack Query cache** (`queryClient.clear()`).
   - Cached queries (notifications, reports, work orders) from the previous citizen session remained in memory, causing potential cross-session data leaks.

---

## 2. The Solution & Architecture

### A. Centralized Role-Based Redirection (`frontend/src/features/auth/routing.ts`)
A dedicated, role-aware routing helper was established:
- **Coordinator / Admin:** Canonical landing is `/coordinator`. Deep links are honored **only** if they begin with `/coordinator`. Citizen paths (`/my-reports`, `/report`, `/track`) are strictly overridden to `/coordinator`.
- **Repair Team:** Canonical landing is `/team/jobs`. Deep links are honored **only** if they begin with `/team`.
- **Citizen:** Canonical landing is `/my-reports`. Citizen cannot be redirected into `/coordinator` or `/team`.

```typescript
export function getAuthorizedRedirect(
  role: string | null | undefined,
  fromPath?: string | null
): string {
  const normRole = (role || 'citizen').toLowerCase() as UserRole;
  const defaultRoute = ROLE_DEFAULT_ROUTES[normRole] || '/my-reports';

  if (!fromPath || fromPath === '/login' || fromPath === '/register' || fromPath === '/') {
    return defaultRoute;
  }

  if (normRole === 'coordinator' || normRole === 'admin') {
    if (fromPath.startsWith('/coordinator')) return fromPath;
    return defaultRoute; // Always defaults to /coordinator
  }

  if (normRole === 'repair_team') {
    if (fromPath.startsWith('/team')) return fromPath;
    return defaultRoute; // Always defaults to /team/jobs
  }

  if (fromPath.startsWith('/coordinator') || fromPath.startsWith('/team')) {
    return defaultRoute; // Always defaults to /my-reports
  }

  return fromPath;
}
```

### B. Session Isolation & Query Cache Purge (`AuthContext.tsx`)
- Integrated `queryClient.clear()` directly into `logout()`. When any user signs out, all cached queries (`notifications`, `reports`, `team-jobs`, `analytics`) are instantly purged from memory.
- Added `isInitializing` state (`true` on startup while validating token with `/auth/me`, `false` once resolved or failed).
- Updated `login(email, password)` to return `Promise<User>`, guaranteeing that `LoginPage` immediately receives the server-verified role.

### C. Bulletproof Route Guards & Loading State (`App.tsx`)
- Added `FullScreenLoading` in `App.tsx`. While `isInitializing` is true, route guards render a clean loading spinner rather than flashing or prematurely redirecting to `/report`.
- Updated unauthorized redirects: if an unauthorized user lands on a protected coordinator route, they are routed safely to `/my-reports` or `/login`, preventing confusion.

### D. Direct Login Auto-Redirect (`LoginPage.tsx`)
- If an already authenticated user visits `/login`, an effect immediately redirects them to their authorized role dashboard without rendering the redundant login form.
- `handleEmailLogin`, `handleGoogleCredentialResponse`, and `handleLinkAccountSubmit` now uniformly pass the verified `user.role` to `getAuthorizedRedirect`.

### E. Clean Logout Navigation Across All Portals
- `CoordinatorLayout.tsx`: `logout(); navigate('/login', { replace: true });`
- `TeamJobsPage.tsx`: `logout(); navigate('/login', { replace: true });`
- `MyReportsPage.tsx`: `logout(); navigate('/login', { replace: true });`
- `PublicHeader.tsx`: `logout(); navigate('/login', { replace: true });` (desktop and mobile).

---

## 3. Files Modified

| File | Change Details |
| :--- | :--- |
| `frontend/src/features/auth/routing.ts` | **New file**: Implemented `getAuthorizedRedirect()` and `ROLE_DEFAULT_ROUTES` with role permission enforcement. |
| `frontend/src/features/auth/AuthContext.tsx` | Added `isInitializing`, `queryClient.clear()` on logout for session isolation, typed `login` return as `Promise<User>`. |
| `frontend/src/pages/LoginPage.tsx` | Integrated `getAuthorizedRedirect`, added auto-redirect for already logged-in users, removed `localStorage` role fallback guessing. |
| `frontend/src/pages/RegisterPage.tsx` | Integrated `getAuthorizedRedirect` for clean post-registration routing. |
| `frontend/src/App.tsx` | Added `FullScreenLoading` while `isInitializing` is true; prevented premature bouncing to `/report`. |
| `frontend/src/components/CoordinatorLayout.tsx` | Clean logout with `replace: true`. |
| `frontend/src/components/PublicHeader.tsx` | Clean React Router logout with `navigate('/login', { replace: true })`, added mobile sign out. |
| `frontend/src/pages/MyReportsPage.tsx` | Clean logout with `replace: true`. |
| `frontend/src/pages/TeamJobsPage.tsx` | Clean logout with `replace: true`. |
| `backend/tests/test_api.py` | Added automated backend integration test `test_role_isolation_and_identity_resolution`. |

---

## 4. Verification & Automated Test Results

### 1. Routing Unit Tests (Node.js Test Runner)
Executed 13 comprehensive unit tests covering all permutations:
```
Testing getAuthorizedRedirect:
  PASS: Coordinator logging in after citizen at /my-reports -> /coordinator
  PASS: Coordinator logging in after citizen at /report -> /coordinator
  PASS: Coordinator deep link to report detail -> /coordinator/reports/123
  PASS: Coordinator default -> /coordinator
  PASS: Coordinator from /login -> /coordinator
  PASS: Citizen blocked from coordinator deep link -> /my-reports
  PASS: Citizen blocked from team portal -> /my-reports
  PASS: Citizen deep link to track report -> /track/PAV-ABC
  PASS: Citizen default -> /my-reports
  PASS: Repair team blocked from citizen page -> /team/jobs
  PASS: Repair team blocked from coordinator -> /team/jobs
  PASS: Repair team deep link to work orders -> /team/jobs
  PASS: Repair team default -> /team/jobs

Result: 13 / 13 passed (100%)
```

### 2. Frontend Production Build & Typecheck
Command: `npm run build`
- TypeScript compiler (`tsc -b`): **0 errors**
- Vite production build: **Success** in 885ms (`dist/` generated).

### 3. Frontend Lint
Command: `npm run lint` (`oxlint`)
- **0 errors** across 40 files.

### 4. Backend Automated Test Suite
Command: `python -m pytest tests/test_api.py -v`
- Total tests: **17 passed** (including new `test_role_isolation_and_identity_resolution`).
- Status: **100% Pass** in 21.4s.

---

## 5. Local Demonstration Instructions (For Tomorrow's Viva/Demo)

### Services Setup
Ensure both servers are running:
- **Backend:** `http://127.0.0.1:8000` (Uvicorn FastAPI)
- **Frontend:** `http://127.0.0.1:5173` (Vite React)

### Step-by-Step Demonstration Script

#### Scenario 1: Citizen to Coordinator Handover (The Exact Bug Scenario)
1. Open [http://127.0.0.1:5173/login](http://127.0.0.1:5173/login).
2. Sign in as Citizen (Google sign-in or `test_citizen@paventra.local` / `CitizenPass123!`).
3. You are taken directly to the Citizen Portal (`/my-reports`).
4. Click "Report damage" and submit a test report (or simply browse reports).
5. Click **"Sign out"**.
6. You are cleanly returned to `/login`.
7. Click "Prefill testing accounts" $\to$ select **Coordinator** (`coordinator@paventra.local` / `Paventra2024!`) $\to$ click **Sign in**.
8. **Verify:** You are taken **DIRECTLY to the Coordinator Dashboard (`/coordinator`)** with the full coordinator sidebar (Dashboard, Reports, Inspections, Map, Teams, Analytics). The citizen interface does **not** appear!

#### Scenario 2: Repair Team Portal
1. From Coordinator Dashboard, click **"Sign out"**.
2. Click "Prefill testing accounts" $\to$ select **Repair Team** (`team.alpha@paventra.local` / `TeamAlpha2024!`) $\to$ click **Sign in**.
3. **Verify:** You are taken directly to `/team/jobs` (Repair Operations Portal).
4. Coordinator and citizen pages are protected and not displayed.

#### Scenario 3: Refresh & Deep Link Integrity
1. While logged in as Coordinator, refresh [http://127.0.0.1:5173/coordinator/reports](http://127.0.0.1:5173/coordinator/reports).
2. **Verify:** The page reloads seamlessly in the Coordinator layout with no flashing or redirection to `/report`.
3. Click "Public Home" in the top bar to view the public site. In the header, note your active "Coordinator" badge. Click it to return instantly to `/coordinator`.
