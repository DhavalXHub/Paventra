/**
 * Resolves uploaded image or media asset URLs safely across environments.
 * - If asset path is already an absolute HTTP/HTTPS URL (e.g., Supabase Storage CDN), returns it directly.
 * - Otherwise, prefixes with VITE_API_URL or relative path for local proxy.
 */
export function resolveAssetUrl(
  pathOrName: string | null | undefined,
  folder: 'reports' | 'completions' | 'inspections' = 'reports'
): string | null {
  if (!pathOrName) return null;

  // Direct cloud CDN URLs (Supabase Storage, S3, Cloudinary)
  if (pathOrName.startsWith('http://') || pathOrName.startsWith('https://')) {
    return pathOrName;
  }

  // Relative path cleanup
  const clean = pathOrName.startsWith('/')
    ? pathOrName
    : `/uploads/${folder}/${pathOrName}`;

  const apiUrl = import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/+$/, '')
    : '';

  return `${apiUrl}${clean}`;
}
