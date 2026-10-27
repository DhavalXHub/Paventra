/**
 * OpenStreetMap Nominatim Geocoding and Reverse Geocoding Utility.
 *
 * Designed for privacy-conscious civic use with:
 * - In-memory LRU-style cache to avoid redundant requests.
 * - Graceful timeout handling (never blocks the reporting wizard).
 * - Clean short-label formatting for road infrastructure contexts.
 */

export interface GeocodingResult {
  place_id: number;
  display_name: string;
  lat: number;
  lon: number;
  shortLabel: string;
}

const reverseCache = new Map<string, { formattedAddress: string; shortLabel: string }>();
const searchCache = new Map<string, GeocodingResult[]>();

function formatShortLabel(item: any): string {
  const addr = item.address || {};
  const parts: string[] = [];

  // Primary road or landmark
  if (addr.road) parts.push(addr.road);
  else if (addr.pedestrian) parts.push(addr.pedestrian);
  else if (addr.suburb) parts.push(addr.suburb);
  else if (addr.neighbourhood) parts.push(addr.neighbourhood);

  // Secondary locality / neighborhood
  if (addr.suburb && !parts.includes(addr.suburb)) parts.push(addr.suburb);
  else if (addr.city_district && !parts.includes(addr.city_district)) parts.push(addr.city_district);

  // City / Town
  const city = addr.city || addr.town || addr.village || addr.county;
  if (city && !parts.includes(city)) parts.push(city);

  if (parts.length > 0) {
    return parts.join(', ');
  }

  // Fallback to first segments of display_name
  const segments = (item.display_name || '').split(',');
  return segments.slice(0, 3).join(', ').trim();
}

/**
 * Search places or street names using OpenStreetMap Nominatim.
 */
export async function searchPlaces(
  query: string,
  signal?: AbortSignal
): Promise<GeocodingResult[]> {
  const trimmed = query.trim();
  if (trimmed.length < 3) return [];

  const cacheKey = trimmed.toLowerCase();
  if (searchCache.has(cacheKey)) {
    return searchCache.get(cacheKey)!;
  }

  // Create internal abort controller with 5-second timeout
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), 5000);

  const combinedSignal = signal
    ? (AbortSignal as any).any
      ? (AbortSignal as any).any([signal, timeoutController.signal])
      : signal
    : timeoutController.signal;

  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
      trimmed
    )}&addressdetails=1&limit=5`;

    const res = await fetch(url, {
      signal: combinedSignal,
      headers: {
        Accept: 'application/json',
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) return [];

    const raw = await res.json();
    if (!Array.isArray(raw)) return [];

    const results: GeocodingResult[] = raw.map((item: any) => ({
      place_id: item.place_id,
      display_name: item.display_name,
      lat: parseFloat(item.lat),
      lon: parseFloat(item.lon),
      shortLabel: formatShortLabel(item),
    }));

    // Cache up to 50 search terms
    if (searchCache.size > 50) {
      const first = searchCache.keys().next().value;
      if (first) searchCache.delete(first);
    }
    searchCache.set(cacheKey, results);

    return results;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') return [];
    console.warn('Geocoding search failed:', err.message);
    return [];
  }
}

/**
 * Reverse geocode latitude and longitude into readable street and district names.
 */
export async function reverseGeocode(
  lat: number,
  lon: number,
  signal?: AbortSignal
): Promise<{ formattedAddress: string; shortLabel: string } | null> {
  // Approximate to ~11m resolution to leverage cache
  const cacheKey = `${lat.toFixed(4)},${lon.toFixed(4)}`;
  if (reverseCache.has(cacheKey)) {
    return reverseCache.get(cacheKey)!;
  }

  // Create internal abort controller with 5-second timeout
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), 5000);

  const combinedSignal = signal
    ? (AbortSignal as any).any
      ? (AbortSignal as any).any([signal, timeoutController.signal])
      : signal
    : timeoutController.signal;

  try {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&addressdetails=1`;

    const res = await fetch(url, {
      signal: combinedSignal,
      headers: {
        Accept: 'application/json',
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) return null;

    const data = await res.json();
    if (!data || !data.display_name) return null;

    const shortLabel = formatShortLabel(data);
    const result = {
      formattedAddress: data.display_name,
      shortLabel: shortLabel || data.display_name.slice(0, 50),
    };

    // Cache up to 100 reverse geocoded points
    if (reverseCache.size > 100) {
      const first = reverseCache.keys().next().value;
      if (first) reverseCache.delete(first);
    }
    reverseCache.set(cacheKey, result);

    return result;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') return null;
    console.warn('Reverse geocoding failed:', err.message);
    return null;
  }
}
