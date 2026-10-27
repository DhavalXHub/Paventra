import React, { useState, useEffect, useRef, useCallback } from 'react';
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Navigation,
  Search,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  MapPin,
  Compass,
} from 'lucide-react';
import { searchPlaces, reverseGeocode, type GeocodingResult } from '../lib/geocoding';

// Fix Leaflet marker icons in Vite bundler
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

interface RideHailingLocationPickerProps {
  initialLat: number | null;
  initialLng: number | null;
  initialAccuracy: number | null;
  initialSource: string;
  initialAddress: string;
  onLocationSelect: (data: {
    lat: number;
    lng: number;
    accuracy: number | null;
    source: 'gps' | 'manual' | 'search';
    addressHint: string;
  }) => void;
}

// Map Controller for smooth flyTo, center tracking, and size invalidation
function MapController({
  onCenterChange,
  setIsMoving,
  flyTarget,
}: {
  onCenterChange: (lat: number, lng: number) => void;
  setIsMoving: (moving: boolean) => void;
  flyTarget: { lat: number; lng: number; zoom?: number } | null;
}) {
  const map = useMap();
  const lastTargetRef = useRef<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    // Force Leaflet to calculate container pixel size immediately on mount
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 150);
    return () => clearTimeout(timer);
  }, [map]);

  useEffect(() => {
    if (!flyTarget) return;
    const prev = lastTargetRef.current;
    if (
      !prev ||
      Math.abs(prev.lat - flyTarget.lat) > 0.00001 ||
      Math.abs(prev.lng - flyTarget.lng) > 0.00001
    ) {
      lastTargetRef.current = { lat: flyTarget.lat, lng: flyTarget.lng };
      map.flyTo([flyTarget.lat, flyTarget.lng], flyTarget.zoom || 17, {
        duration: 0.8,
      });
    }
  }, [flyTarget, map]);

  useMapEvents({
    dragstart() {
      setIsMoving(true);
    },
    drag() {
      setIsMoving(true);
    },
    dragend() {
      setIsMoving(false);
      const c = map.getCenter();
      onCenterChange(c.lat, c.lng);
    },
    zoomend() {
      const c = map.getCenter();
      onCenterChange(c.lat, c.lng);
    },
  });

  return null;
}

export function RideHailingLocationPicker({
  initialLat,
  initialLng,
  initialAccuracy,
  initialSource,
  initialAddress,
  onLocationSelect,
}: RideHailingLocationPickerProps) {
  // Coordinates state
  const [currentLat, setCurrentLat] = useState<number | null>(initialLat);
  const [currentLng, setCurrentLng] = useState<number | null>(initialLng);
  const [accuracy, setAccuracy] = useState<number | null>(initialAccuracy);
  const [locationSource, setLocationSource] = useState<'gps' | 'manual' | 'search'>(
    (initialSource as 'gps' | 'manual' | 'search') || 'manual'
  );
  const [resolvedAddress, setResolvedAddress] = useState<string>(initialAddress);

  // Map & Pin states
  const [isMoving, setIsMoving] = useState(false);
  const [flyTarget, setFlyTarget] = useState<{ lat: number; lng: number; zoom?: number } | null>(
    null
  );

  // GPS states
  const [isLocating, setIsLocating] = useState(false);
  const [gpsError, setGpsError] = useState<string | null>(null);

  // Search states
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<GeocodingResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchResults, setShowSearchResults] = useState(false);
  
  // Refs to prevent dependency loop and unmount cleanup
  const onLocationSelectRef = useRef(onLocationSelect);
  useEffect(() => {
    onLocationSelectRef.current = onLocationSelect;
  }, [onLocationSelect]);

  const resolvedAddressRef = useRef(resolvedAddress);
  useEffect(() => {
    resolvedAddressRef.current = resolvedAddress;
  }, [resolvedAddress]);

  const searchAbortRef = useRef<AbortController | null>(null);
  const reverseAbortRef = useRef<AbortController | null>(null);
  const reverseDebounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const isInitializedRef = useRef(false);

  // Handle outside clicks to close search suggestions
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSearchResults(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Reverse Geocoding with abort control and stable references
  const doReverseGeocode = useCallback(
    async (
      lat: number,
      lng: number,
      source: 'gps' | 'manual' | 'search',
      acc: number | null
    ) => {
      if (reverseAbortRef.current) {
        reverseAbortRef.current.abort();
      }
      reverseAbortRef.current = new AbortController();

      try {
        const result = await reverseGeocode(lat, lng, reverseAbortRef.current.signal);
        const resolved = result?.shortLabel || '';
        if (resolved) {
          setResolvedAddress(resolved);
          resolvedAddressRef.current = resolved;
        }
        onLocationSelectRef.current({
          lat,
          lng,
          accuracy: acc,
          source,
          addressHint: resolved || resolvedAddressRef.current,
        });
      } catch {
        onLocationSelectRef.current({
          lat,
          lng,
          accuracy: acc,
          source,
          addressHint: resolvedAddressRef.current,
        });
      }
    },
    []
  );

  // Request High Accuracy Geolocation
  const requestCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser or operating system.');
      return;
    }

    setIsLocating(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, accuracy: acc } = pos.coords;
        setCurrentLat(latitude);
        setCurrentLng(longitude);
        setAccuracy(acc);
        setLocationSource('gps');
        setIsLocating(false);

        // Fly the map smoothly to the user's real street coordinates
        setFlyTarget({ lat: latitude, lng: longitude, zoom: 17 });

        // Immediately update parent state
        onLocationSelectRef.current({
          lat: latitude,
          lng: longitude,
          accuracy: acc,
          source: 'gps',
          addressHint: resolvedAddressRef.current,
        });

        // Trigger reverse geocode for road hint
        doReverseGeocode(latitude, longitude, 'gps', acc);
      },
      (err) => {
        setIsLocating(false);
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setGpsError(
              'Location permission was denied. You can search an address above or pan the map to place the pin manually.'
            );
            break;
          case err.POSITION_UNAVAILABLE:
            setGpsError(
              'Location information unavailable. Please search for your street or adjust the map pin.'
            );
            break;
          case err.TIMEOUT:
            setGpsError(
              'Location request timed out. Please tap "Locate me" again or pick your spot on the map.'
            );
            break;
          default:
            setGpsError(
              'Could not retrieve GPS coordinates. You can position the pin directly on the map.'
            );
            break;
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 14000,
        maximumAge: 15000,
      }
    );
  }, [doReverseGeocode]);

  // Auto-request location on mount only if coordinates not already established
  useEffect(() => {
    if (isInitializedRef.current) return;
    isInitializedRef.current = true;

    if (initialLat === null || initialLng === null) {
      requestCurrentLocation();
    } else {
      // If returning with existing coordinates, fly map to them
      setFlyTarget({ lat: initialLat, lng: initialLng, zoom: 17 });
      if (!initialAddress) {
        doReverseGeocode(initialLat, initialLng, (initialSource as any) || 'manual', initialAccuracy);
      }
    }

    return () => {
      if (reverseDebounceTimerRef.current) clearTimeout(reverseDebounceTimerRef.current);
      if (reverseAbortRef.current) reverseAbortRef.current.abort();
      if (searchAbortRef.current) searchAbortRef.current.abort();
    };
  }, [initialLat, initialLng, initialAddress, initialAccuracy, initialSource, requestCurrentLocation, doReverseGeocode]);

  // Debounce map center updates as the user pans
  const handleCenterChange = useCallback(
    (lat: number, lng: number) => {
      setCurrentLat(lat);
      setCurrentLng(lng);
      setLocationSource('manual');
      // On manual drag, accuracy radius no longer strictly applies to the pin center
      setAccuracy(null);

      // Immediately inform parent so "Review & Submit" button is enabled
      onLocationSelectRef.current({
        lat,
        lng,
        accuracy: null,
        source: 'manual',
        addressHint: resolvedAddressRef.current,
      });

      // Debounce reverse geocoding on settled center
      if (reverseDebounceTimerRef.current) {
        clearTimeout(reverseDebounceTimerRef.current);
      }
      reverseDebounceTimerRef.current = setTimeout(() => {
        doReverseGeocode(lat, lng, 'manual', null);
      }, 400);
    },
    [doReverseGeocode]
  );

  // Address search with 350ms debounce
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (trimmed.length < 3) {
      return;
    }

    if (searchAbortRef.current) {
      searchAbortRef.current.abort();
    }
    searchAbortRef.current = new AbortController();

    const handler = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchPlaces(trimmed, searchAbortRef.current?.signal);
        setSearchResults(results);
        setShowSearchResults(results.length > 0);
      } finally {
        setIsSearching(false);
      }
    }, 350);

    return () => clearTimeout(handler);
  }, [searchQuery]);

  function handleSelectSearchResult(item: GeocodingResult) {
    setCurrentLat(item.lat);
    setCurrentLng(item.lon);
    setLocationSource('search');
    setAccuracy(null);
    setResolvedAddress(item.shortLabel);
    setSearchQuery('');
    setShowSearchResults(false);

    // Fly to search coordinate
    setFlyTarget({ lat: item.lat, lng: item.lon, zoom: 17 });

    onLocationSelectRef.current({
      lat: item.lat,
      lng: item.lon,
      accuracy: null,
      source: 'search',
      addressHint: item.shortLabel,
    });
  }

  // Initial center fallback (Defaults to reasonable urban center if no GPS yet)
  const defaultCenter: [number, number] =
    currentLat && currentLng ? [currentLat, currentLng] : [19.076, 72.8777];

  return (
    <div className="space-y-3">
      {/* Search Bar with Autocomplete Dropdown */}
      <div ref={searchContainerRef} className="relative z-30">
        <div className="relative flex items-center">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
          <input
            type="text"
            className="w-full pl-10 pr-10 py-2.5 text-sm bg-white border border-stone-200 rounded-lg shadow-sm placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-[#14462a] focus:border-transparent transition-all"
            placeholder="Search street, road or landmark (e.g. MG Road, Indiranagar)…"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              if (!e.target.value.trim()) {
                setSearchResults([]);
                setShowSearchResults(false);
              }
            }}
            onFocus={() => searchResults.length > 0 && setShowSearchResults(true)}
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setShowSearchResults(false);
              }}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-stone-400 hover:text-stone-600 rounded-full hover:bg-stone-100 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          {isSearching && (
            <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
              <Loader2 className="w-4 h-4 text-[#14462a] animate-spin" />
            </div>
          )}
        </div>

        {/* Search Results Dropdown */}
        {showSearchResults && searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1.5 bg-white border border-stone-200 rounded-lg shadow-lg overflow-hidden z-50 max-h-60 overflow-y-auto divide-y divide-stone-100">
            {searchResults.map((item) => (
              <button
                key={item.place_id}
                type="button"
                onClick={() => handleSelectSearchResult(item)}
                className="w-full text-left px-3.5 py-2.5 hover:bg-stone-50 transition-colors flex items-start gap-2.5"
              >
                <MapPin className="w-4 h-4 text-[#14462a] flex-shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-stone-900 truncate">
                    {item.shortLabel}
                  </p>
                  <p className="text-[11px] text-stone-500 truncate mt-0.5">
                    {item.display_name}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Map Viewport Container */}
      <div className="relative w-full h-[360px] sm:h-[400px] rounded-xl overflow-hidden border border-stone-200 shadow-sm bg-stone-100">
        <MapContainer
          center={defaultCenter}
          zoom={currentLat ? 17 : 14}
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
          attributionControl={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
          <MapController
            onCenterChange={handleCenterChange}
            setIsMoving={setIsMoving}
            flyTarget={flyTarget}
          />
        </MapContainer>

        {/* ─── FIXED CENTER PIN OVERLAY (Ride-Hailing Uber/Rapido Style) ─── */}
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-full pointer-events-none z-[450] flex flex-col items-center"
          style={{ marginTop: '0px' }}
        >
          {/* Tooltip badge floating above the pin */}
          <div
            className={`mb-1 px-2.5 py-1 rounded-full text-[11px] font-medium tracking-wide shadow-md transition-all duration-200 border whitespace-nowrap ${
              isMoving
                ? 'bg-[#14462a] text-white border-[#14462a] scale-105 -translate-y-1'
                : 'bg-white text-stone-800 border-stone-200'
            }`}
          >
            {isMoving ? 'Release to set pin' : 'Pin road defect here'}
          </div>

          {/* Precision Pin Graphic */}
          <div
            className={`transition-transform duration-200 ease-out origin-bottom ${
              isMoving ? '-translate-y-2 scale-110' : 'translate-y-0 scale-100'
            }`}
          >
            <svg
              width="36"
              height="48"
              viewBox="0 0 36 48"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="drop-shadow-md"
            >
              {/* Outer Pin Body */}
              <path
                d="M18 0C8.05888 0 0 8.05888 0 18C0 29.5 18 48 18 48C18 48 36 29.5 36 18C36 8.05888 27.9411 0 18 0Z"
                fill="#14462a"
              />
              {/* Inner White Accent Ring */}
              <circle cx="18" cy="18" r="7" fill="white" />
              {/* Center Dark Core */}
              <circle cx="18" cy="18" r="3.5" fill="#14462a" />
            </svg>
          </div>

          {/* Pulse Ripple on Ground */}
          <div
            className={`w-3.5 h-1.5 rounded-full bg-stone-900/30 transition-all duration-200 ${
              isMoving ? 'scale-75 opacity-30' : 'scale-100 opacity-60'
            }`}
          />
        </div>

        {/* Floating Controls Overlay */}
        <div className="absolute right-3 bottom-3 z-[400] flex flex-col gap-2">
          {/* "Locate Me" Button */}
          <button
            type="button"
            onClick={requestCurrentLocation}
            disabled={isLocating}
            title="Center on my current location"
            className="flex items-center gap-1.5 px-3 py-2 bg-white text-stone-700 hover:text-[#14462a] hover:bg-stone-50 active:scale-95 text-xs font-semibold rounded-lg shadow-md border border-stone-200 transition-all disabled:opacity-75"
          >
            {isLocating ? (
              <Loader2 className="w-4 h-4 text-[#14462a] animate-spin" />
            ) : (
              <Compass className="w-4 h-4 text-[#14462a]" />
            )}
            <span className="hidden sm:inline">
              {isLocating ? 'Locating…' : 'Locate me'}
            </span>
          </button>
        </div>

        {/* Small Instruction Banner at Bottom-Left */}
        <div className="absolute left-3 bottom-3 z-[400] bg-white/95 backdrop-blur-sm px-2.5 py-1 rounded-md text-[11px] text-stone-600 shadow-sm border border-stone-200 pointer-events-none flex items-center gap-1.5">
          <Navigation className="w-3 h-3 text-[#14462a]" />
          <span>Move map to position exact pin</span>
        </div>
      </div>

      {/* GPS Error or Permission Notice Banner */}
      {gpsError && (
        <div className="flex items-start gap-2.5 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900">
          <AlertCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">{gpsError}</p>
          </div>
          <button
            type="button"
            onClick={requestCurrentLocation}
            className="text-[11px] font-semibold text-amber-800 underline hover:text-amber-950 flex-shrink-0"
          >
            Retry GPS
          </button>
        </div>
      )}

      {/* ─── Selected Location Summary Card ─── */}
      {currentLat !== null && currentLng !== null && (
        <div className="bg-white p-3.5 rounded-xl border border-stone-200 shadow-sm space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            {/* Source & Accuracy Badge */}
            <div className="flex items-center gap-2">
              {locationSource === 'gps' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  Device GPS
                  {accuracy !== null && (
                    <span className="text-emerald-700 ml-0.5">
                      (±{Math.round(accuracy)}m)
                    </span>
                  )}
                </span>
              )}
              {locationSource === 'manual' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
                  <MapPin className="w-3.5 h-3.5 text-amber-600" />
                  Map Adjusted
                </span>
              )}
              {locationSource === 'search' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-800 border border-blue-200">
                  <Search className="w-3.5 h-3.5 text-blue-600" />
                  Search Result
                </span>
              )}
            </div>

            {/* Decimal Coordinates */}
            <span className="font-mono text-xs text-stone-600 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
              {currentLat.toFixed(5)}, {currentLng.toFixed(5)}
            </span>
          </div>

          {/* Reverse Geocoded Street Hint */}
          <div className="pt-1 border-t border-stone-100">
            <p className="text-[11px] font-medium text-stone-500 uppercase tracking-wider">
              Selected Street / Vicinity
            </p>
            <p className="text-xs font-semibold text-stone-800 mt-0.5">
              {resolvedAddress || 'Coordinates pinned. Add landmark or road details below.'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
