import type { AnalysisResult, PolygonCoords, StacSearchResponse, ThermalSpring } from "@/types/analysis";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function searchStac(params: {
  west: number;
  south: number;
  east: number;
  north: number;
  start_date: string;
  end_date: string;
  max_items?: number;
}): Promise<StacSearchResponse> {
  return request<StacSearchResponse>("/api/stac/search", {
    method: "POST",
    body: JSON.stringify({
      bbox: {
        west: params.west,
        south: params.south,
        east: params.east,
        north: params.north,
      },
      start_date: params.start_date,
      end_date: params.end_date,
      max_items: params.max_items ?? 10,
    }),
  });
}

export function runAnalysis(params: {
  coordinates: PolygonCoords;
  start_date: string;
  end_date: string;
}): Promise<AnalysisResult> {
  return request<AnalysisResult>("/api/analysis/run", {
    method: "POST",
    body: JSON.stringify({
      polygon: { type: "Polygon", coordinates: params.coordinates },
      start_date: params.start_date,
      end_date: params.end_date,
    }),
  });
}

export function fetchSprings(): Promise<ThermalSpring[]> {
  return request<ThermalSpring[]>("/api/analysis/layers/springs");
}

export function fetchFaults(): Promise<GeoJSON.FeatureCollection> {
  return request<GeoJSON.FeatureCollection>("/api/analysis/layers/faults");
}

export function bboxFromPolygon(coords: PolygonCoords): {
  west: number;
  south: number;
  east: number;
  north: number;
} {
  const ring = coords[0];
  const lons = ring.map((p) => p[0]);
  const lats = ring.map((p) => p[1]);
  return {
    west: Math.min(...lons),
    south: Math.min(...lats),
    east: Math.max(...lons),
    north: Math.max(...lats),
  };
}
