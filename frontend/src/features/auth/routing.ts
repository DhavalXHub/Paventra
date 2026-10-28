import type { UserRole } from '../../types';

export const ROLE_DEFAULT_ROUTES: Record<UserRole, string> = {
  coordinator: '/coordinator',
  admin: '/coordinator',
  repair_team: '/team/jobs',
  citizen: '/my-reports',
};

/**
 * Returns the verified, role-authorized destination path.
 * Ensures coordinators go directly to coordinator routes, repair teams go to team routes,
 * and citizens go to citizen routes, preventing cross-role route trapping or stale fromPath hijacking.
 */
export function getAuthorizedRedirect(
  role: string | null | undefined,
  fromPath?: string | null
): string {
  const normRole = (role || 'citizen').toLowerCase() as UserRole;
  const defaultRoute = ROLE_DEFAULT_ROUTES[normRole] || '/my-reports';

  if (!fromPath || fromPath === '/login' || fromPath === '/register' || fromPath === '/') {
    return defaultRoute;
  }

  // Validate fromPath authorization based on user role
  if (normRole === 'coordinator' || normRole === 'admin') {
    // Coordinators can deep-link into coordinator routes
    if (fromPath.startsWith('/coordinator')) {
      return fromPath;
    }
    // If fromPath was a citizen page (e.g. /my-reports, /report), always send coordinator to their dashboard!
    return defaultRoute;
  }

  if (normRole === 'repair_team') {
    if (fromPath.startsWith('/team')) {
      return fromPath;
    }
    return defaultRoute;
  }

  // Citizens can never deep-link into /coordinator or /team
  if (fromPath.startsWith('/coordinator') || fromPath.startsWith('/team')) {
    return defaultRoute;
  }

  // Valid citizen/public paths (e.g. /my-reports, /track, /report)
  return fromPath;
}
