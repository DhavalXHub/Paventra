import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { MapMarker } from '../types';
import { StatusBadge, SeverityBadge } from './Badge';
import { formatRelative } from '../lib/constants';
import { MAP_MARKER_COLORS } from '../lib/constants';

// Fix Leaflet default icons in Vite
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

function createColoredIcon(color: string) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="36" viewBox="0 0 24 36">
    <path d="M12 0C5.37 0 0 5.37 0 12c0 9 12 24 12 24s12-15 12-24C24 5.37 18.63 0 12 0z"
      fill="${color}" stroke="white" stroke-width="1.5"/>
    <circle cx="12" cy="12" r="5" fill="white" opacity="0.9"/>
  </svg>`;
  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [24, 36],
    iconAnchor: [12, 36],
    popupAnchor: [0, -36],
  });
}

// Location picker component
function LocationPicker({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// ─── Report Map (coordinator view) ────────────────────────────────────────────

interface ReportMapProps {
  markers: MapMarker[];
  height?: string;
}

export function ReportMap({ markers, height = '400px' }: ReportMapProps) {
  // Compute center: India default if no markers
  const center: [number, number] = markers.length > 0
    ? [markers.reduce((s, m) => s + m.lat, 0) / markers.length,
       markers.reduce((s, m) => s + m.lon, 0) / markers.length]
    : [20.5937, 78.9629];

  return (
    <MapContainer
      center={center}
      zoom={markers.length > 0 ? 12 : 5}
      style={{ height, width: '100%', borderRadius: '8px' }}
      zoomControl={false}
    >
      <ZoomControl position="bottomright" />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {markers.map((m) => (
        <Marker
          key={m.id}
          position={[m.lat, m.lon]}
          icon={createColoredIcon(MAP_MARKER_COLORS[m.status] ?? '#6b7280')}
        >
          <Popup>
            <div className="text-xs space-y-1 min-w-[160px]">
              <p className="font-semibold text-gray-900">{m.public_ref}</p>
              <StatusBadge status={m.status} />
              {m.severity && <SeverityBadge severity={m.severity} />}
              <p className="text-gray-500">{m.damage_type.replace(/_/g, ' ')}</p>
              {m.priority_score !== null && (
                <p className="text-gray-500">Priority: {m.priority_score.toFixed(0)}/100</p>
              )}
              <p className="text-gray-400">{formatRelative(m.created_at)}</p>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

// ─── Location Picker (citizen submit) ────────────────────────────────────────

interface LocationPickerMapProps {
  lat: number | null;
  lng: number | null;
  onPick: (lat: number, lng: number) => void;
  height?: string;
}

export function LocationPickerMap({ lat, lng, onPick, height = '260px' }: LocationPickerMapProps) {
  const center: [number, number] = lat && lng ? [lat, lng] : [20.5937, 78.9629];

  return (
    <div style={{ height, width: '100%', borderRadius: '8px', overflow: 'hidden' }}>
      <MapContainer
        center={center}
        zoom={lat ? 15 : 5}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <LocationPicker onPick={onPick} />
        {lat && lng && (
          <Marker position={[lat, lng]} icon={createColoredIcon('#16a34a')}>
            <Popup>
              <span className="text-xs">Selected location<br />{lat.toFixed(5)}, {lng.toFixed(5)}</span>
            </Popup>
          </Marker>
        )}
      </MapContainer>
    </div>
  );
}
